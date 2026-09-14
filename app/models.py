import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from sqlalchemy import inspect, text
from sqlmodel import Field, SQLModel, create_engine

# Single database configuration supporting SQLite locally and PostgreSQL/Neon in production
DB_URL = os.environ.get("DATABASE_URL", "sqlite:///./campusops.db")
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif DB_URL.startswith("postgresql://"):
    DB_URL = DB_URL.replace("postgresql://", "postgresql+psycopg://", 1)

_connect_args = {"check_same_thread": False} if DB_URL.startswith("sqlite") else {}
engine = create_engine(DB_URL, connect_args=_connect_args)


class Case(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tenant_id: str = "nust"
    workflow_type: str = "verification"  # verification | coordination | escalation | general
    title: Optional[str] = None
    priority: str = "medium"  # low | medium | high | urgent
    
    # Request & Subject context
    student_number: Optional[str] = None
    caller_name: Optional[str] = None
    phone: str
    country_code: str = "NA"
    original_query: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Agent Planning
    intent: Optional[str] = None
    category: Optional[str] = None
    reasoning: Optional[str] = None
    plan_confidence: Optional[str] = None  # low | medium | high
    preparer_used: Optional[str] = None  # gemini | groq | deterministic
    should_call: Optional[bool] = True
    plan_json: Optional[str] = None  # Structured multi-step execution plan

    # Workflow Execution State
    status: str = "received"  # received | planning | in_progress | verifying | resolved | escalated | failed
    current_step_index: int = 0
    total_steps: int = 1
    steps_json: Optional[str] = None  # List of executed/pending steps

    # Active/Latest Call tracking
    call_attempts: int = 0
    run_id: Optional[str] = None
    call_status: Optional[str] = None  # in_progress | completed | no_answer | declined | failed
    structured_result_json: Optional[str] = None
    transcript_json: Optional[str] = None
    completion_confidence: Optional[float] = None
    task_completed: Optional[bool] = None
    evidence_json: Optional[str] = None  # list[str]

    # Verification Loop
    verification_status: Optional[str] = None  # verified | incomplete | contradiction | not_required
    verification_score: Optional[float] = None  # 0.0 - 1.0
    verification_json: Optional[str] = None  # Detailed checklist & missing fields

    # Routing & Escalation
    channel: Optional[str] = None  # phone | email | in_person | route
    channel_reason: Optional[str] = None
    routed_office: Optional[str] = None
    routed_contact: Optional[str] = None
    routed_reason: Optional[str] = None
    escalation_json: Optional[str] = None  # Staff escalation packet & action recommendation

    # Knowledge & Provenance
    retrieved_sources_json: Optional[str] = None
    no_kb_coverage: Optional[bool] = None


# Helpers for JSON serialization/deserialization
def get_plan(case: Case) -> Optional[Dict[str, Any]]:
    return json.loads(case.plan_json) if case.plan_json else None


def set_plan(case: Case, value: Optional[Dict[str, Any]]) -> None:
    case.plan_json = json.dumps(value) if value is not None else None


def get_steps(case: Case) -> List[Dict[str, Any]]:
    return json.loads(case.steps_json) if case.steps_json else []


def set_steps(case: Case, value: Optional[List[Dict[str, Any]]]) -> None:
    case.steps_json = json.dumps(value) if value is not None else None


def get_verification(case: Case) -> Optional[Dict[str, Any]]:
    return json.loads(case.verification_json) if case.verification_json else None


def set_verification(case: Case, value: Optional[Dict[str, Any]]) -> None:
    case.verification_json = json.dumps(value) if value is not None else None


def get_escalation(case: Case) -> Optional[Dict[str, Any]]:
    return json.loads(case.escalation_json) if case.escalation_json else None


def set_escalation(case: Case, value: Optional[Dict[str, Any]]) -> None:
    case.escalation_json = json.dumps(value) if value is not None else None


def get_structured_result(case: Case) -> Optional[dict]:
    return json.loads(case.structured_result_json) if case.structured_result_json else None


def set_structured_result(case: Case, value: Optional[dict]) -> None:
    case.structured_result_json = json.dumps(value) if value is not None else None


def get_transcript(case: Case) -> Optional[str]:
    if not case.transcript_json:
        return None
    value = json.loads(case.transcript_json)
    return value if isinstance(value, str) else json.dumps(value)


def set_transcript(case: Case, value: Optional[str]) -> None:
    case.transcript_json = json.dumps(value) if value is not None else None


def get_retrieved_sources(case: Case) -> Optional[list]:
    return json.loads(case.retrieved_sources_json) if case.retrieved_sources_json else None


def set_retrieved_sources(case: Case, value: Optional[list]) -> None:
    case.retrieved_sources_json = json.dumps(value) if value else None


def get_evidence(case: Case) -> Optional[list]:
    return json.loads(case.evidence_json) if case.evidence_json else None


def set_evidence(case: Case, value: Optional[list]) -> None:
    case.evidence_json = json.dumps(value) if value else None


def _ensure_columns() -> None:
    """Idempotently ensures all newer columns exist if running against an existing database."""
    inspector = inspect(engine)
    if "case" not in inspector.get_table_names():
        return
    columns = {c["name"] for c in inspector.get_columns("case")}
    with engine.begin() as conn:
        new_cols = {
            "workflow_type": "VARCHAR DEFAULT 'verification'",
            "title": "VARCHAR",
            "priority": "VARCHAR DEFAULT 'medium'",
            "plan_json": "VARCHAR",
            "current_step_index": "INTEGER DEFAULT 0",
            "total_steps": "INTEGER DEFAULT 1",
            "steps_json": "VARCHAR",
            "verification_status": "VARCHAR",
            "verification_score": "FLOAT",
            "verification_json": "VARCHAR",
            "escalation_json": "VARCHAR",
            "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
            "country_code": "VARCHAR DEFAULT 'NA'",
            "task_completed": "BOOLEAN",
            "evidence_json": "VARCHAR",
        }
        for col, col_type in new_cols.items():
            if col not in columns:
                try:
                    conn.execute(text(f'ALTER TABLE "case" ADD COLUMN {col} {col_type}'))
                except Exception:
                    pass


def _ensure_dedup_index() -> None:
    with engine.begin() as conn:
        try:
            conn.execute(
                text(
                    'CREATE UNIQUE INDEX IF NOT EXISTS ix_case_open_dedup '
                    'ON "case" (tenant_id, phone, original_query) '
                    "WHERE status NOT IN ('resolved', 'escalated', 'failed')"
                )
            )
        except Exception:
            pass


def init_db() -> None:
    from . import models_student  # noqa: F401
    SQLModel.metadata.create_all(engine)
    _ensure_columns()
    _ensure_dedup_index()
