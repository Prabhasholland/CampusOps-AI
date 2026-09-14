"""Tests for Escalation Engine in CampusOps AI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.escalation import EscalationEngine
from app.directory import directory as campus_directory
from app.calle.results import CallResult


def test_escalation_packet_creation():
    engine = EscalationEngine()
    student = campus_directory.lookup_student("220034567")
    call_result = CallResult(
        status="completed",
        structured_result={
            "application_status": "pending_documents",
            "payment_status": "blocked",
            "expected_date": None,
        },
        transcript="bot: May I check payment status?\nuser: The payment is currently blocked because tax affidavit is missing.",
        evidence=["Payment blocked pending affidavit inspection."],
    )

    packet = engine.build_packet(
        case_id=42,
        workflow_type="verification",
        original_query="Verify scholarship delay for student Josef Kambala",
        student=student,
        call_results=[call_result],
        verification_data={"missing_fields": ["expected_date"]},
        tenant={"id": "nust"},
    )

    assert packet.case_id == 42
    assert "Financial Aid" in packet.routed_office or "Scholarship" in packet.routed_office
    assert len(packet.recommended_staff_actions) >= 2
    assert len(packet.verified_evidence) >= 1
    assert any("blocked" in q.lower() for q in packet.key_transcript_quotes)


def main():
    test_escalation_packet_creation()
    print("PASS  test_escalation_packet_creation")
    print("\nAll escalation tests passed successfully!")


if __name__ == "__main__":
    main()
