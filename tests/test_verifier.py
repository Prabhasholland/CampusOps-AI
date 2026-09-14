"""Tests for Evidence Verification Engine in CampusOps AI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.verifier import EvidenceVerifier
from app.calle.results import CallResult


def test_scholarship_verification_success():
    verifier = EvidenceVerifier()
    call_result = CallResult(
        status="completed",
        task_completed=True,
        completion_confidence=0.94,
        structured_result={
            "application_status": "approved",
            "payment_status": "pending",
            "expected_date": "2026-09-18",
            "additional_action_required": False,
            "resolved": True,
        },
        evidence=["Officer confirmed student file is approved and payment is scheduled for Sept 18."],
    )

    ver = verifier.verify_scholarship(call_result)
    assert ver.is_verified is True
    assert ver.status == "VERIFIED"
    assert ver.next_action == "RESOLVE_CASE"
    assert ver.score >= 0.85
    assert len(ver.missing_fields) == 0


def test_scholarship_verification_blocked_action_required():
    verifier = EvidenceVerifier()
    call_result = CallResult(
        status="completed",
        task_completed=True,
        completion_confidence=0.65,
        structured_result={
            "application_status": "pending_documents",
            "payment_status": "blocked",
            "expected_date": None,
            "additional_action_required": True,
            "student_action_description": "Submit parental tax affidavit.",
            "resolved": False,
        },
    )

    ver = verifier.verify_scholarship(call_result)
    assert ver.is_verified is True  # Valid finding that action is needed
    assert ver.status == "ACTION_REQUIRED"
    assert ver.next_action == "ESCALATE_TO_STAFF"


def test_coordination_step_verification():
    verifier = EvidenceVerifier()
    call_result = CallResult(
        status="completed",
        structured_result={
            "is_available": True,
            "confirmed_slot": "Tuesday 2:00 PM",
            "resolved": True,
        },
        completion_confidence=0.95,
    )

    ver = verifier.verify_coordination_step(call_result, role="student")
    assert ver.is_verified is True
    assert ver.status == "VERIFIED"
    assert ver.next_action == "RESOLVE_CASE"


def main():
    test_scholarship_verification_success()
    print("PASS  test_scholarship_verification_success")
    test_scholarship_verification_blocked_action_required()
    print("PASS  test_scholarship_verification_blocked_action_required")
    test_coordination_step_verification()
    print("PASS  test_coordination_step_verification")
    print("\nAll verifier tests passed successfully!")


if __name__ == "__main__":
    main()
