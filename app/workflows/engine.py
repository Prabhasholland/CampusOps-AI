"""Workflow Execution Engine for CampusOps AI.

Orchestrates multi-step phone workflows, async polling, verification loops,
and human escalation state transitions.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, Any

from sqlmodel import Session, select

from ..directory import directory as campus_directory, StudentRecord
from ..calle.client import CalleClient
from ..calle.schemas import get_schema_for_workflow
from ..models import (
    Case,
    engine,
    set_plan,
    set_steps,
    set_verification,
    set_escalation,
    set_structured_result,
    set_transcript,
    set_evidence,
    set_retrieved_sources,
)
from ..tenants import load_tenant
from ..agents.planner import planner, ExecutionPlan, PlanStep
from ..agents.escalation import escalation_engine
from .base import WorkflowContext, StepOutcome
from .verification_flow import VerificationWorkflow
from .coordination_flow import CoordinationWorkflow
from .escalation_flow import DirectEscalationWorkflow

logger = logging.getLogger(__name__)

default_calle = CalleClient()
calle = default_calle

POLL_WAIT_FIRST_LIVE = 45
POLL_INTERVAL_LIVE = 6
POLL_WAIT_FIRST_MOCK = 2
POLL_INTERVAL_MOCK = 1.5
MAX_CALL_ATTEMPTS = 3


class WorkflowEngine:
    """Stateful coordinator for CampusOps autonomous operations."""

    def __init__(self, calle_client: Optional[CalleClient] = None):
        self.calle = calle_client or default_calle
        self._workflows = {
            "verification": VerificationWorkflow(),
            "coordination": CoordinationWorkflow(),
            "escalation": DirectEscalationWorkflow(),
            "general": DirectEscalationWorkflow(),
        }

    def _get_workflow(self, workflow_type: str):
        return self._workflows.get(workflow_type, self._workflows["general"])

    async def run(self, case_id: int) -> None:
        try:
            with Session(engine) as session:
                case = session.get(Case, case_id)
                if not case:
                    return

                tenant = load_tenant(case.tenant_id)
                student = (
                    campus_directory.lookup_student(case.student_number)
                    if case.student_number
                    else None
                )

                # Step A: AI Operational Planning Pass
                case.status = "planning"
                session.add(case)
                session.commit()

                plan: ExecutionPlan = planner.plan(case.original_query, student, tenant)
                case.workflow_type = plan.workflow_type
                case.intent = plan.intent
                case.priority = plan.priority
                case.reasoning = plan.reasoning
                case.plan_confidence = plan.confidence
                case.preparer_used = plan.preparer_used
                case.should_call = plan.should_call
                case.total_steps = len(plan.steps)
                case.title = f"{plan.workflow_type.capitalize()}: {plan.intent.replace('_', ' ').capitalize()}"
                set_plan(case, plan.to_dict())

                if plan.sources_used:
                    set_retrieved_sources(case, plan.sources_used)

                # If safety guardrails dictate immediate escalation without dialing
                if not plan.should_call:
                    packet = escalation_engine.build_packet(
                        case_id=case.id,
                        workflow_type=plan.workflow_type,
                        original_query=case.original_query,
                        student=student,
                        call_results=[],
                        tenant=tenant,
                    )
                    case.status = "escalated"
                    case.routed_office = packet.routed_office
                    case.routed_contact = packet.routed_contact
                    case.routed_reason = packet.root_cause
                    set_escalation(case, packet.to_dict())
                    session.add(case)
                    session.commit()
                    return

                session.add(case)
                session.commit()

            # Execute Workflow Steps
            await self._execute_workflow_steps(case_id, plan, tenant, student)

        except Exception as exc:
            logger.exception("Workflow execution encountered an unhandled error for case %s: %s", case_id, exc)
            self._mark_failed(case_id, str(exc))

    async def _execute_workflow_steps(
        self,
        case_id: int,
        plan: ExecutionPlan,
        tenant: dict,
        student: Optional[StudentRecord],
    ) -> None:
        workflow = self._get_workflow(plan.workflow_type)
        context = WorkflowContext(
            case_id=case_id,
            tenant_id=tenant.get("id", "nust"),
            tenant_config=tenant,
            student=student,
            plan=plan,
        )

        current_step_idx = 0

        while current_step_idx < len(plan.steps):
            step = workflow.get_current_step(context, current_step_idx)
            if not step:
                break

            # Update DB to in_progress for this step
            with Session(engine) as session:
                case = session.get(Case, case_id)
                if not case or case.status in ["resolved", "escalated", "failed"]:
                    return
                case.status = "in_progress"
                case.current_step_index = current_step_idx + 1
                session.add(case)
                session.commit()

            # Dispatch CALL-E Call for this step
            # Dispatch CALL-E Call for this step
            schema = get_schema_for_workflow(plan.workflow_type, step.schema_type)
            task_prompt = self._build_step_task_prompt(step, plan, tenant, student)
            
            run_id = self.calle.dispatch(
                task=task_prompt,
                phone=step.target_phone,
                result_schema=schema,
            )

            with Session(engine) as session:
                case = session.get(Case, case_id)
                case.run_id = run_id
                case.call_status = "calling"
                case.call_attempts = 1
                session.add(case)
                session.commit()

            # Poll for Call Result
            wait_first = POLL_WAIT_FIRST_LIVE if self.calle.is_live else POLL_WAIT_FIRST_MOCK
            await asyncio.sleep(wait_first)
            call_result = await self._poll_call_until_terminal(run_id)

            # Evaluate Step Outcome via Workflow
            outcome: StepOutcome = workflow.evaluate_step(context, step, call_result)
            context.executed_steps.append(outcome)

            # Persist Step Result to DB
            with Session(engine) as session:
                case = session.get(Case, case_id)
                if not case or case.status in ["resolved", "escalated", "failed"]:
                    return

                case.call_status = call_result.status
                set_structured_result(case, call_result.structured_result)
                set_transcript(case, call_result.transcript)
                case.completion_confidence = call_result.completion_confidence
                case.task_completed = call_result.task_completed
                set_evidence(case, call_result.evidence)
                set_steps(case, [s.to_dict() for s in context.executed_steps])

                if outcome.verification:
                    case.verification_status = outcome.verification.status
                    case.verification_score = outcome.verification.score
                    set_verification(case, outcome.verification.to_dict())

                if context.escalation_packet:
                    case.status = "escalated"
                    case.routed_office = context.escalation_packet.routed_office
                    case.routed_contact = context.escalation_packet.routed_contact
                    case.routed_reason = context.escalation_packet.root_cause
                    set_escalation(case, context.escalation_packet.to_dict())
                    session.add(case)
                    session.commit()
                    return

                if outcome.is_terminal:
                    case.status = "resolved"
                    session.add(case)
                    session.commit()
                    return

                session.add(case)
                session.commit()

            if outcome.next_step_index is not None:
                current_step_idx = outcome.next_step_index
            else:
                current_step_idx += 1

    async def _poll_call_until_terminal(self, run_id: str):
        poll_interval = POLL_INTERVAL_LIVE if self.calle.is_live else POLL_INTERVAL_MOCK
        while True:
            result = self.calle.get_result(run_id)
            if result.status != "in_progress":
                return result
            sleep_duration = result.poll_after_seconds or poll_interval
            await asyncio.sleep(sleep_duration)

    def _build_step_task_prompt(
        self,
        step: PlanStep,
        plan: ExecutionPlan,
        tenant: dict,
        student: Optional[StudentRecord],
    ) -> str:
        intro = tenant.get("agent_intro", "Hello, I am calling on behalf of NUST.")
        lines = [
            intro,
            f"You are speaking with {step.target_name} ({step.target_role.replace('_', ' ').title()}) at phone number {step.target_phone}.",
            f"Purpose of this call: {step.task_instructions}",
            f"Context: {plan.briefing}",
        ]
        if student:
            lines.append(f"Student details: {student.name} (Student Number: {student.student_number}).")

        lines.append(
            "Be professional, clear, and direct. Capture all required structured details accurately. "
            "Never disclose confidential student information to unverified third parties."
        )
        return "\n\n".join(lines)

    def _mark_failed(self, case_id: int, error_message: str) -> None:
        with Session(engine) as session:
            case = session.get(Case, case_id)
            if case:
                case.status = "failed"
                case.call_status = f"error: {error_message[:200]}"
                session.add(case)
                session.commit()


# Engine singleton
engine_instance = WorkflowEngine()


async def handle_workflow_execution(case_id: int) -> None:
    await engine_instance.run(case_id)


async def resume_workflow_execution(case_id: int) -> None:
    await engine_instance.run(case_id)
