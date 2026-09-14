"""Plain-assertion tests for the student directory swap (JSONDirectory ->
SqlDirectory) and channel-aware task building - no pytest dependency.

Run directly: python tests/test_student_directory.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.directory import JSONDirectory, SqlDirectory  # noqa: E402
from app.dispatcher import build_task  # noqa: E402
from app.models import engine, init_db  # noqa: E402
from app.schemas import PROOF_OF_REG, SUBJECT_CANCELLATION, TRIAGE  # noqa: E402
from app.tenants import load_tenant  # noqa: E402

init_db()
_tenant = load_tenant("nust")


def test_sql_directory_returns_same_shape_as_json_directory():
    json_student = JSONDirectory().lookup("220012345")
    sql_student = SqlDirectory(engine).lookup("220100002")
    assert json_student is not None, "app/data/students.json fixture missing 220012345"
    assert sql_student is not None, "run scripts/seed_students.py --target sqlite first"

    for attr in ("student_number", "name", "phone", "registration_status", "fee_balance", "subjects"):
        assert hasattr(json_student, attr), attr
        assert hasattr(sql_student, attr), attr

    assert isinstance(sql_student.subjects, list)
    if sql_student.subjects:
        subject = sql_student.subjects[0]
        for attr in ("code", "name", "drop_deadline"):
            assert hasattr(subject, attr), attr


def test_channel_enum_rejects_invalid_values():
    for schema in (PROOF_OF_REG, SUBJECT_CANCELLATION, TRIAGE):
        channel_prop = schema["properties"]["channel"]
        assert channel_prop["enum"] == ["phone", "email", "in_person", "route"]
        assert "channel" in schema["required"]


def test_disability_never_appears_in_task_string():
    student = SqlDirectory(engine).lookup("220100009")  # disability-flagged demo case
    assert student is not None, "run scripts/seed_students.py --target sqlite first"
    assert student.disability, "fixture should have a disability value set to test against"

    from app.models import Case

    case = Case(
        tenant_id="nust", student_number="220100009", phone="+264810000009",
        original_query="Can you tell me what's on file for me?", intent="other",
    )
    task = build_task(case, student, _tenant, briefing="")
    assert student.disability not in task
    assert "disability" not in task.lower() or "disability status" in task.lower()
    # The word "disability" is allowed only inside the instruction telling the
    # agent never to state it - not as a stated fact about this student.
    assert "never state" in task.lower() or "disability accommodations" in task.lower()


def test_office_directory_present_in_every_task():
    from app.models import Case

    case = Case(
        tenant_id="nust", phone="+264810000000",
        original_query="What are the office hours?", intent="other", caller_name="Test Caller",
    )
    task = build_task(case, None, _tenant, briefing="office hours briefing")
    for office in _tenant["offices"].values():
        assert office["email"] in task
        assert office["location"] in task


def main() -> None:
    tests = [obj for name, obj in sorted(globals().items()) if name.startswith("test_")]
    failures = 0
    for test in tests:
        try:
            test()
            print(f"PASS  {test.__name__}")
        except AssertionError as exc:
            failures += 1
            print(f"FAIL  {test.__name__}: {exc}")
    if failures:
        print(f"\n{failures} of {len(tests)} tests failed")
        raise SystemExit(1)
    print(f"\nAll {len(tests)} tests passed")


if __name__ == "__main__":
    main()
