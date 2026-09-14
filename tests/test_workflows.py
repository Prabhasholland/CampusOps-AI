"""End-to-end integration tests for CampusOps AI Workflows."""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlmodel import Session, select
from app.models import Case, engine, init_db, get_plan, get_verification, get_escalation, get_steps
from app.calle.client import CalleClient
from app.workflows.engine import WorkflowEngine


def test_workflow_scholarship_verification_flow():
    init_db()
    with Session(engine) as session:
        case = Case(
            tenant_id="nust",
            workflow_type="verification",
            phone="+264811234567",
            student_number="220012345",
            caller_name="Tunga Amutenya",
            original_query="A student's scholarship is delayed. Find out the status, release date, and resolve it.",
            status="received",
        )
        session.add(case)
        session.commit()
        session.refresh(case)
        case_id = case.id

    workflow_engine = WorkflowEngine(calle_client=CalleClient(force_mock=True))
    asyncio.run(workflow_engine.run(case_id))

    with Session(engine) as session:
        updated = session.get(Case, case_id)
        assert updated.status == "resolved"
        assert updated.call_status == "completed"
        assert updated.verification_status == "VERIFIED"
        assert updated.verification_score >= 0.85
        ver = get_verification(updated)
        assert ver is not None
        assert ver["extracted_facts"]["application_status"] == "approved"
        assert ver["extracted_facts"]["expected_date"] == "2026-09-18"


def test_workflow_multi_party_coordination_flow():
    init_db()
    with Session(engine) as session:
        case = Case(
            tenant_id="nust",
            workflow_type="coordination",
            phone="+264812345678",
            student_number="220023456",
            caller_name="Maria Nghipandulwa",
            original_query="Schedule an academic advising meeting between the student, faculty advisor Dr. Johannes Alweendo, and FCI department office.",
            status="received",
        )
        session.add(case)
        session.commit()
        session.refresh(case)
        case_id = case.id

    workflow_engine = WorkflowEngine(calle_client=CalleClient(force_mock=True))
    asyncio.run(workflow_engine.run(case_id))

    with Session(engine) as session:
        updated = session.get(Case, case_id)
        assert updated.status == "resolved"
        steps = get_steps(updated)
        assert len(steps) == 3
        assert steps[0]["target_role"] == "student"
        assert steps[1]["target_role"] == "faculty"
        assert steps[2]["target_role"] == "department_office"


def test_workflow_insufficient_evidence_escalation_flow():
    init_db()
    with Session(engine) as session:
        case = Case(
            tenant_id="nust",
            workflow_type="verification",
            phone="+264813456789",  # Triggers missing tax affidavit scenario
            student_number="220034567",
            caller_name="Josef Kambala",
            original_query="Verify financial aid release for Josef Kambala regarding delayed allowance.",
            status="received",
        )
        session.add(case)
        session.commit()
        session.refresh(case)
        case_id = case.id

    workflow_engine = WorkflowEngine(calle_client=CalleClient(force_mock=True))
    asyncio.run(workflow_engine.run(case_id))

    with Session(engine) as session:
        updated = session.get(Case, case_id)
        assert updated.status == "escalated"
        assert updated.routed_office is not None
        esc = get_escalation(updated)
        assert esc is not None
        assert len(esc["recommended_staff_actions"]) >= 1


def main():
    test_workflow_scholarship_verification_flow()
    print("PASS  test_workflow_scholarship_verification_flow")
    test_workflow_multi_party_coordination_flow()
    print("PASS  test_workflow_multi_party_coordination_flow")
    test_workflow_insufficient_evidence_escalation_flow()
    print("PASS  test_workflow_insufficient_evidence_escalation_flow")
    print("\nAll workflow integration tests passed successfully!")


if __name__ == "__main__":
    main()
