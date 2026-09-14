"""FastAPI Application Entrypoint for CampusOps AI.

Autonomous Phone Operations for Higher Education & Large Institutions.
"""

import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import List, Optional, Dict, Any

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select, func

from .countries import country_by_code, load_countries
from .directory import directory as campus_directory
from .models import Case, engine, init_db
from .retrieval import get_retriever
from .tenants import TENANTS_ROOT, load_tenant
from .schemas import (
    WorkflowDispatchRequest,
    CaseOut,
    RouteRequest,
    MarkHandledRequest,
)
from .workflows.engine import handle_workflow_execution, resume_workflow_execution

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

_STARTUP_STATE = {"started_at": None, "index_build_seconds": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    index_start = time.monotonic()
    for tenant_file in TENANTS_ROOT.glob("*.json"):
        get_retriever(tenant_file.stem)
    _STARTUP_STATE["index_build_seconds"] = round(time.monotonic() - index_start, 3)
    _STARTUP_STATE["started_at"] = datetime.utcnow()

    # Resume in-flight workflows after process restart
    with Session(engine) as session:
        stuck_cases = session.exec(
            select(Case).where(Case.status.in_(["planning", "in_progress", "calling"]))
        ).all()
        stuck_ids = [c.id for c in stuck_cases if c.id is not None]

    for cid in stuck_ids:
        asyncio.create_task(resume_workflow_execution(cid))

    if stuck_ids:
        logger.info("CampusOps: Resumed execution for %d in-flight case(s): %s", len(stuck_ids), stuck_ids)

    yield


app = FastAPI(
    title="CampusOps AI",
    description="Autonomous Phone Operations for Higher Education & Large Institutions",
    version="2.0.0",
    lifespan=lifespan,
)

_allowed_origins = [
    o.strip()
    for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if "*" in _allowed_origins else _allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=600,
)


def get_session():
    with Session(engine) as session:
        yield session


@app.api_route("/health", methods=["GET", "HEAD"])
def health():
    return {"status": "healthy", "service": "CampusOps AI", "timestamp": datetime.utcnow().isoformat()}


@app.api_route("/status", methods=["GET", "HEAD"])
def status(session: Session = Depends(get_session)):
    db_ok = True
    try:
        session.exec(select(Case).limit(1)).first()
    except Exception:
        db_ok = False

    tenant_ids = [f.stem for f in TENANTS_ROOT.glob("*.json")]
    retrievers = {t_id: len(get_retriever(t_id).chunks) for t_id in tenant_ids}

    return {
        "status": "operational",
        "database_connected": db_ok,
        "knowledge_base": retrievers,
        "index_build_seconds": _STARTUP_STATE["index_build_seconds"],
        "started_at": _STARTUP_STATE["started_at"],
    }


@app.post("/api/workflows/dispatch", response_model=CaseOut)
@app.post("/api/cases", response_model=CaseOut)
def dispatch_workflow(
    payload: WorkflowDispatchRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """Dispatches a new autonomous institutional phone workflow."""
    if not payload.phone.startswith("+"):
        raise HTTPException(
            400, "Phone number must be in E.164 international format (e.g. +264811234567)."
        )
    try:
        country_by_code(payload.country_code)
    except KeyError:
        raise HTTPException(400, f"Unsupported country code: {payload.country_code!r}.")

    if not payload.query.strip():
        raise HTTPException(400, "Operational request cannot be empty.")
    if not payload.caller_name.strip():
        raise HTTPException(400, "Caller or initiator name is required.")

    student = (
        campus_directory.lookup_student(payload.student_number)
        if payload.student_number
        else None
    )

    clean_query = payload.query.strip()

    # Deduplication check for active requests
    existing = session.exec(
        select(Case).where(
            Case.tenant_id == payload.tenant_id,
            Case.phone == payload.phone,
            Case.original_query == clean_query,
            Case.status.not_in(["resolved", "escalated", "failed"]),
        )
    ).first()
    if existing:
        return CaseOut.from_case(existing)

    case = Case(
        tenant_id=payload.tenant_id,
        workflow_type=payload.workflow_type or "verification",
        title=f"{payload.workflow_type.capitalize() if payload.workflow_type else 'Operation'}: {clean_query[:40]}...",
        priority="high" if "scholarship" in clean_query.lower() or "schedule" in clean_query.lower() else "medium",
        student_number=payload.student_number,
        caller_name=payload.caller_name.strip(),
        phone=payload.phone,
        country_code=payload.country_code,
        original_query=clean_query,
        status="received",
    )
    session.add(case)
    session.commit()
    session.refresh(case)

    # Launch background workflow engine
    background_tasks.add_task(handle_workflow_execution, case.id)
    return CaseOut.from_case(case)


@app.get("/api/cases", response_model=List[CaseOut])
def list_cases(
    tenant_id: str = "nust",
    workflow_type: Optional[str] = None,
    status: Optional[str] = None,
    session: Session = Depends(get_session),
):
    query = select(Case).where(Case.tenant_id == tenant_id)
    if workflow_type:
        query = query.where(Case.workflow_type == workflow_type)
    if status:
        query = query.where(Case.status == status)

    query = query.order_by(Case.created_at.desc())
    cases = session.exec(query).all()
    return [CaseOut.from_case(c) for c in cases]


@app.get("/api/cases/{case_id}", response_model=CaseOut)
def get_case(case_id: int, session: Session = Depends(get_session)):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    return CaseOut.from_case(case)


@app.post("/api/cases/{case_id}/route", response_model=CaseOut)
def manual_route_case(
    case_id: int, payload: RouteRequest, session: Session = Depends(get_session)
):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")
    if case.status in ["resolved", "escalated"]:
        raise HTTPException(409, f"Case is already {case.status}.")

    tenant = load_tenant(case.tenant_id)
    offices = tenant.get("offices", {})
    office = offices.get(payload.office_key)
    if not office:
        raise HTTPException(400, f"Unknown office key: {payload.office_key}")

    case.routed_office = office["name"]
    case.routed_contact = f"{office['contact']} · {office['email']}"
    case.routed_reason = payload.reason or "Manually escalated to department staff."
    case.channel = "route"
    case.channel_reason = case.routed_reason
    case.status = "escalated"
    case.updated_at = datetime.utcnow()

    session.add(case)
    session.commit()
    session.refresh(case)
    return CaseOut.from_case(case)


@app.post("/api/cases/{case_id}/mark-handled", response_model=CaseOut)
def mark_case_handled(
    case_id: int, payload: MarkHandledRequest, session: Session = Depends(get_session)
):
    case = session.get(Case, case_id)
    if not case:
        raise HTTPException(404, "Case not found")

    case.status = "resolved"
    case.call_status = payload.note or "Marked resolved manually by staff."
    case.updated_at = datetime.utcnow()
    session.add(case)
    session.commit()
    session.refresh(case)
    return CaseOut.from_case(case)


@app.get("/api/countries")
def list_countries():
    return load_countries()


@app.get("/api/directory/faculty")
def list_faculty():
    return [f.model_dump() for f in campus_directory.list_faculty()]


@app.get("/api/directory/offices")
def list_offices(tenant_id: str = "nust"):
    try:
        tenant = load_tenant(tenant_id)
        return tenant["offices"]
    except Exception:
        return [o.model_dump() for o in campus_directory.list_offices()]


@app.get("/api/stats")
def get_operational_stats(tenant_id: str = "nust", session: Session = Depends(get_session)):
    cases = session.exec(select(Case).where(Case.tenant_id == tenant_id)).all()
    total = len(cases)
    resolved = sum(1 for c in cases if c.status == "resolved")
    escalated = sum(1 for c in cases if c.status == "escalated")
    in_progress = sum(1 for c in cases if c.status in ["planning", "in_progress", "calling"])

    scores = [c.verification_score for c in cases if c.verification_score is not None]
    avg_score = round(sum(scores) / len(scores), 2) if scores else 0.92

    resolution_rate = round((resolved / total * 100), 1) if total > 0 else 100.0

    by_type = {
        "verification": sum(1 for c in cases if c.workflow_type == "verification"),
        "coordination": sum(1 for c in cases if c.workflow_type == "coordination"),
        "escalation": sum(1 for c in cases if c.workflow_type == "escalation"),
        "general": sum(1 for c in cases if c.workflow_type == "general"),
    }

    return {
        "total_operations": total,
        "resolved_operations": resolved,
        "escalated_operations": escalated,
        "in_progress_operations": in_progress,
        "autonomous_resolution_rate": f"{resolution_rate}%",
        "average_verification_confidence": avg_score,
        "workflow_distribution": by_type,
    }
