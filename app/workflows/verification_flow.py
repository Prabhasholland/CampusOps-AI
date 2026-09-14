"""Workflow 1: Autonomous Status Verification Flow.

Orchestrates verification of scholarship disbursements, academic eligibility, and administrative statuses.
"""

from typing import Optional, List
from .base import BaseWorkflow, WorkflowContext, StepOutcome
from ..agents.planner import PlanStep
from ..agents.verifier import verifier, VerificationResult
from ..agents.escalation import escalation_engine
from ..calle.results import CallResult


class VerificationWorkflow(BaseWorkflow):
    """Workflow 1: Scholarship & Administrative Status Verification."""

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
        # Run Evidence Verification Engine
        verification = verifier.verify_scholarship(result, required_fields=step.required_fields)

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

        if verification.next_action == "RESOLVE_CASE":
            outcome.is_terminal = True
        elif verification.next_action == "ESCALATE_TO_STAFF" or verification.status in ["ACTION_REQUIRED", "INCOMPLETE_EVIDENCE"]:
            context.escalation_packet = escalation_engine.build_packet(
                case_id=context.case_id,
                workflow_type="verification",
                original_query=context.plan.briefing,
                student=context.student,
                call_results=[result],
                verification_data=verification.to_dict(),
                tenant=context.tenant_config,
            )
            outcome.is_terminal = True
        elif verification.next_action == "TRIGGER_FOLLOW_UP_CALL":
            # If multi-step configured, advance to step 2
            if len(context.plan.steps) > step.step_number:
                outcome.is_terminal = False
                outcome.next_step_index = step.step_number  # 0-indexed next step
            else:
                context.escalation_packet = escalation_engine.build_packet(
                    case_id=context.case_id,
                    workflow_type="verification",
                    original_query=context.plan.briefing,
                    student=context.student,
                    call_results=[result],
                    verification_data=verification.to_dict(),
                    tenant=context.tenant_config,
                )
                outcome.is_terminal = True

        return outcome
