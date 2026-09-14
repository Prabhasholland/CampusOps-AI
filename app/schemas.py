"""API Request & Response Schemas for CampusOps AI."""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from .models import (
    Case,
    get_plan,
    get_steps,
    get_verification,
    get_escalation,
    get_structured_result,
    get_transcript,
    get_evidence,
    get_retrieved_sources,
)
from .directory import directory as campus_directory
from .calle.schemas import (
    PROOF_OF_REG_SCHEMA as PROOF_OF_REG,
    SUBJECT_CANCELLATION_SCHEMA as SUBJECT_CANCELLATION,
    TRIAGE_SCHEMA as TRIAGE,
    SCHOLARSHIP_VERIFICATION_SCHEMA,
    COORDINATION_SLOT_SCHEMA,
)



class WorkflowDispatchRequest(BaseModel):
    query: str
    workflow_type: Optional[str] = "verification"  # verification | coordination | escalation | general
    phone: str
    country_code: str = "NA"
    caller_name: str
    student_number: Optional[str] = None
    tenant_id: str = "nust"


# Backward compatibility alias
IntakeRequest = WorkflowDispatchRequest


class RouteRequest(BaseModel):
    office_key: str
    reason: Optional[str] = None


class MarkHandledRequest(BaseModel):
    note: Optional[str] = None


class CaseOut(BaseModel):
    id: int
    tenant_id: str
    workflow_type: str
    title: Optional[str]
    priority: str
    status: str
    original_query: str
    created_at: datetime
    updated_at: datetime

    # Entity details
    student_number: Optional[str]
    student_name: Optional[str]
    caller_name: Optional[str]
    phone: str
    country_code: str

    # Execution Plan
    intent: Optional[str]
    category: Optional[str]
    reasoning: Optional[str]
    plan_confidence: Optional[str]
    preparer_used: Optional[str]
    should_call: Optional[bool]
    plan: Optional[Dict[str, Any]]

    # Step Execution
    current_step_index: int
    total_steps: int
    steps: List[Dict[str, Any]]

    # Active Call Details
    call_attempts: int
    call_status: Optional[str]
    run_id: Optional[str]
    structured_result: Optional[dict]
    transcript: Optional[str]
    completion_confidence: Optional[float]
    task_completed: Optional[bool]
    evidence: Optional[list]

    # Verification Loop
    verification_status: Optional[str]
    verification_score: Optional[float]
    verification: Optional[Dict[str, Any]]

    # Escalation & Routing
    channel: Optional[str]
    channel_reason: Optional[str]
    routed_office: Optional[str]
    routed_contact: Optional[str]
    routed_reason: Optional[str]
    escalation: Optional[Dict[str, Any]]

    # Knowledge Base
    retrieved_sources: Optional[list]
    no_kb_coverage: Optional[bool]

    @classmethod
    def from_case(cls, case: Case) -> "CaseOut":
        student = (
            campus_directory.lookup_student(case.student_number)
            if case.student_number
            else None
        )
        return cls(
            id=case.id,
            tenant_id=case.tenant_id,
            workflow_type=case.workflow_type or "verification",
            title=case.title or f"{case.workflow_type.capitalize()} Operation",
            priority=case.priority or "medium",
            status=case.status,
            original_query=case.original_query,
            created_at=case.created_at,
            updated_at=case.updated_at or case.created_at,
            student_number=case.student_number,
            student_name=student.name if student else None,
            caller_name=case.caller_name,
            phone=case.phone,
            country_code=case.country_code,
            intent=case.intent,
            category=case.category,
            reasoning=case.reasoning,
            plan_confidence=case.plan_confidence,
            preparer_used=case.preparer_used,
            should_call=case.should_call,
            plan=get_plan(case),
            current_step_index=case.current_step_index or 0,
            total_steps=case.total_steps or 1,
            steps=get_steps(case),
            call_attempts=case.call_attempts,
            call_status=case.call_status,
            run_id=case.run_id,
            structured_result=get_structured_result(case),
            transcript=get_transcript(case),
            completion_confidence=case.completion_confidence,
            task_completed=case.task_completed,
            evidence=get_evidence(case),
            verification_status=case.verification_status,
            verification_score=case.verification_score,
            verification=get_verification(case),
            channel=case.channel,
            channel_reason=case.channel_reason,
            routed_office=case.routed_office,
            routed_contact=case.routed_contact,
            routed_reason=case.routed_reason,
            escalation=get_escalation(case),
            retrieved_sources=get_retrieved_sources(case),
            no_kb_coverage=case.no_kb_coverage,
        )
