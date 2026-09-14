"""Workflow 3: Direct Escalation & Exception Triage Flow in CampusOps AI."""

from typing import Optional
from .base import BaseWorkflow, WorkflowContext, StepOutcome
from ..agents.planner import PlanStep
from ..agents.verifier import verifier
from ..agents.escalation import escalation_engine
from ..calle.results import CallResult


class DirectEscalationWorkflow(BaseWorkflow):
    """Workflow 3: Handles sensitive matters and standard academic inquiries."""

    def get_current_step(self, context: WorkflowContext, step_index: int) -> Optional[PlanStep]:
        if step_index < len(context.plan.steps):
            return context.plan.steps[step_index]
        return None

    def evaluate_step(
        self,
        context: WorkflowContext,
        step: PlanStep,
        result: CallResult,
    ) -> StepOutcome:
        verification = verifier.verify_general(result)

        outcome = StepOutcome(
            step_number=step.step_number,
            target_name=step.target_name,
            target_role=step.target_role,
            target_phone=step.target_phone,
            run_id=getattr(result, "run_id", "mock"),
            call_result=result,
            verification=verification,
            is_terminal=True,
            next_step_index=None,
        )

        context.final_verification = verification

        if not verification.is_verified:
            context.escalation_packet = escalation_engine.build_packet(
                case_id=context.case_id,
                workflow_type="general",
                original_query=context.plan.briefing,
                student=context.student,
                call_results=[result],
                verification_data=verification.to_dict(),
                tenant=context.tenant_config,
            )

        return outcome
