"""Base Workflow definitions for CampusOps AI Operations."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

from ..directory import StudentRecord
from ..calle.results import CallResult
from ..agents.planner import ExecutionPlan, PlanStep
from ..agents.verifier import VerificationResult
from ..agents.escalation import EscalationPacket


@dataclass
class StepOutcome:
    step_number: int
    target_name: str
    target_role: str
    target_phone: str
    run_id: str
    call_result: Optional[CallResult] = None
    verification: Optional[VerificationResult] = None
    is_terminal: bool = False
    next_step_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_number": self.step_number,
            "target_name": self.target_name,
            "target_role": self.target_role,
            "target_phone": self.target_phone,
            "run_id": self.run_id,
            "call_status": self.call_result.status if self.call_result else "in_progress",
            "structured_result": self.call_result.structured_result if self.call_result else None,
            "transcript": self.call_result.transcript if self.call_result else None,
            "evidence": self.call_result.evidence if self.call_result else None,
            "completion_confidence": self.call_result.completion_confidence if self.call_result else None,
            "verification": self.verification.to_dict() if self.verification else None,
            "is_terminal": self.is_terminal,
        }


@dataclass
class WorkflowContext:
    case_id: int
    tenant_id: str
    tenant_config: dict
    student: Optional[StudentRecord]
    plan: ExecutionPlan
    executed_steps: List[StepOutcome] = field(default_factory=list)
    final_verification: Optional[VerificationResult] = None
    escalation_packet: Optional[EscalationPacket] = None


class BaseWorkflow(ABC):
    """Abstract Base Class for autonomous phone operations workflows."""

    @abstractmethod
    def get_current_step(self, context: WorkflowContext, step_index: int) -> Optional[PlanStep]:
        """Returns the PlanStep definition for the given index."""
        pass

    @abstractmethod
    def evaluate_step(
        self,
        context: WorkflowContext,
        step: PlanStep,
        result: CallResult,
    ) -> StepOutcome:
        """Evaluates step result, runs verification, and determines next action."""
        pass
