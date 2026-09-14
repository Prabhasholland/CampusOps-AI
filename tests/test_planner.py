"""Tests for Operational AI Planner in CampusOps AI."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.agents.planner import DeterministicPlanner
from app.directory import directory as campus_directory


def test_scholarship_verification_plan():
    planner = DeterministicPlanner()
    student = campus_directory.lookup_student("220012345")
    tenant = {"id": "nust", "short_name": "NUST"}

    plan = planner.plan(
        query="A student's scholarship is delayed. Find out the status and resolve it.",
        student=student,
        tenant=tenant,
    )

    assert plan.workflow_type == "verification"
    assert plan.intent == "scholarship_verification"
    assert plan.should_call is True
    assert len(plan.steps) >= 1
    assert "application_status" in plan.required_facts
    assert "payment_status" in plan.required_facts
    assert "expected_date" in plan.required_facts


def test_multi_party_coordination_plan():
    planner = DeterministicPlanner()
    student = campus_directory.lookup_student("220023456")
    tenant = {"id": "nust", "short_name": "NUST"}

    plan = planner.plan(
        query="Schedule a meeting between the student, faculty advisor Dr. Alweendo, and department office.",
        student=student,
        tenant=tenant,
    )

    assert plan.workflow_type == "coordination"
    assert plan.intent == "multi_party_coordination"
    assert plan.should_call is True
    assert len(plan.steps) == 3
    assert plan.steps[0].target_role == "student"
    assert plan.steps[1].target_role == "faculty"
    assert plan.steps[2].target_role == "department_office"


def test_sensitive_escalation_plan():
    planner = DeterministicPlanner()
    student = campus_directory.lookup_student("220012345")
    tenant = {"id": "nust", "short_name": "NUST"}

    plan = planner.plan(
        query="Student requires legal counsel and police reporting for disciplinary hearing.",
        student=student,
        tenant=tenant,
    )

    assert plan.workflow_type == "escalation"
    assert plan.should_call is False
    assert plan.route_to is not None


def main():
    test_scholarship_verification_plan()
    print("PASS  test_scholarship_verification_plan")
    test_multi_party_coordination_plan()
    print("PASS  test_multi_party_coordination_plan")
    test_sensitive_escalation_plan()
    print("PASS  test_sensitive_escalation_plan")
    print("\nAll planner tests passed successfully!")


if __name__ == "__main__":
    main()
