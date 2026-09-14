"""Human Escalation Engine for CampusOps AI.

Generates comprehensive, actionable escalation packets for university administrators
when automated workflows detect policy blockers, incomplete evidence, or sensitive exceptions.
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Dict, Optional, Any

from ..directory import directory as campus_directory, StudentRecord
from ..calle.results import CallResult


@dataclass
class EscalationPacket:
    case_id: Optional[int]
    workflow_type: str
    original_query: str
    routed_office: str
    routed_contact: str
    urgency: str  # routine | deadline_driven | urgent
    root_cause: str
    verified_evidence: List[str] = field(default_factory=list)
    missing_elements: List[str] = field(default_factory=list)
    key_transcript_quotes: List[str] = field(default_factory=list)
    recommended_staff_actions: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EscalationEngine:
    """Constructs structured staff review packets."""

    def build_packet(
        self,
        case_id: Optional[int],
        workflow_type: str,
        original_query: str,
        student: Optional[StudentRecord],
        call_results: List[CallResult],
        verification_data: Optional[Dict[str, Any]] = None,
        tenant: Optional[dict] = None,
    ) -> EscalationPacket:
        tenant_offices = tenant.get("offices", {}) if tenant else {}
        
        # Determine appropriate office
        office_key = "registrar"
        if workflow_type == "verification" or "scholarship" in original_query.lower():
            office_key = "scholarship"
        elif workflow_type == "coordination" or "advising" in original_query.lower():
            office_key = "fci_department"
        elif "fee" in original_query.lower() or "balance" in original_query.lower():
            office_key = "fees"

        office_info = campus_directory.lookup_office(office_key)
        if office_info:
            routed_office = office_info.name
            routed_contact = f"{office_info.officer_name} · {office_info.email} ({office_info.phone})"
        elif office_key in tenant_offices:
            to = tenant_offices[office_key]
            routed_office = to.get("name", "Office")
            routed_contact = f"{to.get('contact', '')} · {to.get('email', '')}"
        else:
            routed_office = "Office of the Registrar"
            routed_contact = "Academic Administration · registrar@nust.na"

        # Analyze root cause and evidence
        verified_evidence = []
        key_quotes = []
        missing_elements = (verification_data or {}).get("missing_fields", [])
        
        for res in call_results:
            if res.evidence:
                verified_evidence.extend(res.evidence)
            if res.transcript:
                for line in res.transcript.split("\n"):
                    if any(kw in line.lower() for kw in ["blocked", "missing", "require", "cannot", "affidavit", "reject", "conflict"]):
                        key_quotes.append(line.strip())

        # Determine recommendations based on workflow
        recommendations = []
        if workflow_type == "verification":
            root_cause = "Autonomous verification reached financial aid bureau; disbursement is blocked by outstanding documentation."
            recommendations = [
                f"Review student {student.student_number if student else 'record'} for pending financial aid verification forms.",
                "Send an automated SMS/Email advising the student to present the required certified documents to Counter 4.",
                "Once documents are inspected, update the disbursement batch status in the SIS.",
            ]
            urgency = "deadline_driven"
        elif workflow_type == "coordination":
            root_cause = "Multi-party scheduling negotiation encountered a calendar conflict or venue unavailability."
            recommendations = [
                "Inspect open calendar intervals for the faculty advisor and department conference room.",
                "Manually propose an alternate date directly to the student via portal message.",
            ]
            urgency = "routine"
        else:
            root_cause = "Caller request requires administrative discretion, identity document verification, or manual override."
            recommendations = [
                "Review original student inquiry in the context of their academic transcript.",
                "Follow up directly via phone or email during standard office hours.",
            ]
            urgency = "routine"

        return EscalationPacket(
            case_id=case_id,
            workflow_type=workflow_type,
            original_query=original_query,
            routed_office=routed_office,
            routed_contact=routed_contact,
            urgency=urgency,
            root_cause=root_cause,
            verified_evidence=verified_evidence[:5],
            missing_elements=missing_elements,
            key_transcript_quotes=key_quotes[:3],
            recommended_staff_actions=recommendations,
        )


# Singleton instance
escalation_engine = EscalationEngine()
