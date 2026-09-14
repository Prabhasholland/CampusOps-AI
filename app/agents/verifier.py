"""Evidence Verification Engine for CampusOps AI.

Implements the post-call verification loop to ensure that phone calls produce
sufficient, unambiguous, and high-confidence evidence before resolving a case.
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from ..calle.results import CallResult


@dataclass
class EvidenceCheckItem:
    field_name: str
    label: str
    satisfied: bool
    value: Any = None
    note: str = ""


@dataclass
class VerificationResult:
    is_verified: bool
    status: str  # VERIFIED | INCOMPLETE_EVIDENCE | ACTION_REQUIRED | CONTRADICTION | FAILED
    score: float  # 0.0 - 1.0
    extracted_facts: Dict[str, Any] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)
    checklist: List[EvidenceCheckItem] = field(default_factory=list)
    next_action: str = "RESOLVE_CASE"  # RESOLVE_CASE | TRIGGER_FOLLOW_UP_CALL | ESCALATE_TO_STAFF
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_verified": self.is_verified,
            "status": self.status,
            "score": self.score,
            "extracted_facts": self.extracted_facts,
            "missing_fields": self.missing_fields,
            "checklist": [asdict(item) for item in self.checklist],
            "next_action": self.next_action,
            "notes": self.notes,
        }


class EvidenceVerifier:
    """Evaluates structured call output against operational requirements."""

    CONFIDENCE_THRESHOLD = 0.80

    def verify_scholarship(
        self,
        call_result: CallResult,
        required_fields: Optional[List[str]] = None,
    ) -> VerificationResult:
        if required_fields is None:
            required_fields = ["application_status", "payment_status", "expected_date"]

        extracted = call_result.structured_result or {}
        confidence = call_result.completion_confidence or extracted.get("confidence", 0.70)
        checklist: List[EvidenceCheckItem] = []
        missing: List[str] = []

        # Check Application Status
        app_status = extracted.get("application_status")
        has_app = app_status in ["approved", "under_review", "pending_documents", "rejected"]
        checklist.append(
            EvidenceCheckItem(
                field_name="application_status",
                label="Application Status Confirmed",
                satisfied=has_app,
                value=app_status,
                note=f"Status: {app_status}" if has_app else "Missing application status",
            )
        )
        if not has_app:
            missing.append("application_status")

        # Check Payment Status
        pay_status = extracted.get("payment_status")
        has_pay = pay_status in ["paid", "pending", "scheduled", "blocked", "not_applicable"]
        checklist.append(
            EvidenceCheckItem(
                field_name="payment_status",
                label="Disbursement State Verified",
                satisfied=has_pay,
                value=pay_status,
                note=f"Disbursement: {pay_status}" if has_pay else "Missing payment status",
            )
        )
        if not has_pay:
            missing.append("payment_status")

        # Check Expected Date
        exp_date = extracted.get("expected_date")
        # If application is blocked/pending_documents, expected_date might legitimately be unavailable
        has_date = bool(exp_date and exp_date != "None") or pay_status in ["blocked", "paid"]
        checklist.append(
            EvidenceCheckItem(
                field_name="expected_date",
                label="Release Date / Milestone Established",
                satisfied=has_date,
                value=exp_date or ("N/A (Blocked)" if pay_status == "blocked" else None),
                note=f"Date: {exp_date}" if exp_date else ("Not applicable (Blocked)" if pay_status == "blocked" else "Release date missing"),
            )
        )
        if not has_date and "expected_date" in required_fields:
            missing.append("expected_date")

        # Compute Evidence Score
        satisfied_count = sum(1 for item in checklist if item.satisfied)
        total_count = len(checklist)
        score = round((satisfied_count / total_count) * 0.5 + min(1.0, confidence) * 0.5, 2)

        # Decision Logic
        if pay_status == "blocked" or extracted.get("additional_action_required") is True:
            return VerificationResult(
                is_verified=True,
                status="ACTION_REQUIRED",
                score=score,
                extracted_facts=extracted,
                missing_fields=missing,
                checklist=checklist,
                next_action="ESCALATE_TO_STAFF",
                notes="Verification identified that scholarship disbursement is blocked and requires student/staff paperwork.",
            )

        if missing:
            return VerificationResult(
                is_verified=False,
                status="INCOMPLETE_EVIDENCE",
                score=score,
                extracted_facts=extracted,
                missing_fields=missing,
                checklist=checklist,
                next_action="TRIGGER_FOLLOW_UP_CALL" if score > 0.4 else "ESCALATE_TO_STAFF",
                notes=f"Evidence incomplete: missing critical fields {', '.join(missing)}.",
            )

        if score >= self.CONFIDENCE_THRESHOLD and extracted.get("resolved") is True:
            return VerificationResult(
                is_verified=True,
                status="VERIFIED",
                score=score,
                extracted_facts=extracted,
                missing_fields=[],
                checklist=checklist,
                next_action="RESOLVE_CASE",
                notes="All required evidence verified with high confidence. Case ready for automatic resolution.",
            )

        return VerificationResult(
            is_verified=False,
            status="INCOMPLETE_EVIDENCE",
            score=score,
            extracted_facts=extracted,
            missing_fields=missing,
            checklist=checklist,
            next_action="ESCALATE_TO_STAFF",
            notes="Confidence score below acceptable threshold for automated resolution.",
        )

    def verify_coordination_step(
        self,
        call_result: CallResult,
        role: str,
    ) -> VerificationResult:
        extracted = call_result.structured_result or {}
        confidence = call_result.completion_confidence or extracted.get("confidence", 0.85)
        is_avail = extracted.get("is_available", False)
        slot = extracted.get("confirmed_slot") or extracted.get("preferred_slot")

        checklist = [
            EvidenceCheckItem(
                field_name="is_available",
                label=f"{role.capitalize()} Availability Confirmed",
                satisfied=bool(is_avail),
                value=is_avail,
                note="Available" if is_avail else "Participant unavailable",
            ),
            EvidenceCheckItem(
                field_name="confirmed_slot",
                label="Agreed Time Slot Established",
                satisfied=bool(slot),
                value=slot,
                note=f"Slot: {slot}" if slot else "No agreed slot",
            ),
        ]

        missing = []
        if not is_avail:
            missing.append("is_available")
        if not slot:
            missing.append("confirmed_slot")

        score = 0.95 if (is_avail and slot) else 0.40

        if is_avail and slot:
            return VerificationResult(
                is_verified=True,
                status="VERIFIED",
                score=score,
                extracted_facts=extracted,
                missing_fields=[],
                checklist=checklist,
                next_action="RESOLVE_CASE",
                notes=f"{role.capitalize()} confirmed availability for slot '{slot}'.",
            )
        else:
            return VerificationResult(
                is_verified=False,
                status="INCOMPLETE_EVIDENCE",
                score=score,
                extracted_facts=extracted,
                missing_fields=missing,
                checklist=checklist,
                next_action="ESCALATE_TO_STAFF",
                notes=f"{role.capitalize()} could not reach agreement on candidate slots.",
            )

    def verify_general(self, call_result: CallResult) -> VerificationResult:
        extracted = call_result.structured_result or {}
        resolved = extracted.get("resolved") is True
        score = call_result.completion_confidence or 0.85

        checklist = [
            EvidenceCheckItem(
                field_name="resolved",
                label="Inquiry Confirmed Resolved on Call",
                satisfied=resolved,
                value=resolved,
                note="Resolved" if resolved else "Requires human follow-up",
            )
        ]

        return VerificationResult(
            is_verified=resolved,
            status="VERIFIED" if resolved else "ACTION_REQUIRED",
            score=score if resolved else 0.50,
            extracted_facts=extracted,
            missing_fields=[] if resolved else ["resolved"],
            checklist=checklist,
            next_action="RESOLVE_CASE" if resolved else "ESCALATE_TO_STAFF",
            notes="General query verified against caller confirmation." if resolved else "Query left unresolved.",
        )


# Singleton instance
verifier = EvidenceVerifier()
