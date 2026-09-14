"""Workflow 2: Multi-Party Coordination Flow.

Orchestrates sequential phone negotiation across Student, Faculty Advisor, and Department Office.
"""

from typing import Optional, List
from .base import BaseWorkflow, WorkflowContext, StepOutcome
from ..agents.planner import PlanStep
from ..agents.verifier import verifier, VerificationResult
from ..agents.escalation import escalation_engine
from ..calle.results import CallResult


class CoordinationWorkflow(BaseWorkflow):
    """Workflow 2: Multi-Party Advising & Meeting Coordination."""

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
        verification = verifier.verify_coordination_step(result, role=step.target_role)

        outcome = StepOutcome(
            step_number=step.step_number,
            target_name=step.target_name,
            target_role=step.target_role,
            target_phone=step.target_phone,
            run_id=getattr(result, "run_id", "mock"),
            call_result=result,
            verification=verification,
            is_terminal=False,
            next_step_index=None,
        )

        # Check if participant confirmed availability
        if verification.is_verified:
            next_idx = step.step_number  # next step index (since step_number is 1-indexed)
            if next_idx < len(context.plan.steps):
                outcome.is_terminal = False
                outcome.next_step_index = next_idx
            else:
                # All multi-party steps successfully completed
                outcome.is_terminal = True
                context.final_verification = verification
        else:
            # Coordination conflict or unavailable participant
            outcome.is_terminal = True
            all_results = [s.call_result for s in context.executed_steps if s.call_result] + [result]
            context.escalation_packet = escalation_engine.build_packet(
                case_id=context.case_id,
                workflow_type="coordination",
                original_query=context.plan.briefing,
                student=context.student,
                call_results=all_results,
                verification_data=verification.to_dict(),
                tenant=context.tenant_config,
            )

        return outcome
