"""Plain-assertion tests for parse_call_response — no pytest dependency.

Run directly: python tests/test_parse_call_response.py

Confirms the parser matches CALL-E's real output shape, captured directly
from a completed real call on 2026-08-28 (tests/fixtures/real_call_happy.json):
no top-level "result" wrapper at all - task_completed, completion_confidence,
evidence, summary, and post_summary sit directly on the response, the
schema-shaped data lives at recipients[0].structured_result, and the
transcript at recipients[0].attempts[-1].transcript_turns (a list of
{speaker, text}, not a flat string). Every earlier version of this parser
read result.extracted / result.outcome.* / result.transcript instead, none
of which exist on a real payload - see calle_client.py's module docstring
for how that stayed invisible until a dispatcher bug (cases always routing,
never resolving) traced back to it.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.calle_client import parse_call_response  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"


def test_minimal_no_answer_does_not_raise():
    result = parse_call_response({"run_id": "call_1", "status": "NO ANSWER"})
    assert result.status == "no_answer"
    assert result.structured_result is None
    assert result.transcript is None
    assert result.completion_confidence is None


def test_in_progress_statuses():
    for raw in ("PREPARING", "SCHEDULED", "QUEUED", "queued"):
        result = parse_call_response({"run_id": "call_1", "status": raw})
        assert result.status == "in_progress", raw


def test_missing_status_treated_as_in_progress_not_a_crash():
    result = parse_call_response({"run_id": "call_1"})
    assert result.status == "in_progress"


def test_completed_with_full_envelope():
    raw = {
        "run_id": "call_1",
        "status": "COMPLETED",
        "task_completed": True,
        "completion_confidence": {"score": 0.91, "label": "high"},
        "evidence": ["Student confirmed student number."],
        "summary": "Call resolved cleanly.",
        "post_summary": "No follow-up needed.",
        "recipients": [
            {
                "structured_result": {"resolved": True, "identity_confirmed": True},
                "attempts": [
                    {
                        "transcript_turns": [
                            {"speaker": "bot", "text": "Hi..."},
                            {"speaker": "user", "text": "Hello."},
                        ]
                    }
                ],
            }
        ],
    }
    result = parse_call_response(raw)
    assert result.status == "completed"
    assert result.structured_result == {"resolved": True, "identity_confirmed": True}
    assert result.completion_confidence == 0.91
    assert result.task_completed is True
    assert result.evidence == ["Student confirmed student number."]
    assert result.transcript == "bot: Hi...\nuser: Hello."
    assert result.summary == "Call resolved cleanly."
    assert result.post_summary == "No follow-up needed."


def test_real_happy_path_fixture_parses_correctly():
    raw = json.loads((FIXTURES / "real_call_happy.json").read_text(encoding="utf-8"))
    result = parse_call_response(raw)
    assert result.status == "completed"
    assert result.structured_result["resolved"] is True
    assert result.structured_result["category"] == "academic_records"
    assert "Semester 1" in result.transcript or "bot:" in result.transcript
    assert result.task_completed is True
    assert result.completion_confidence == 0.9
    assert result.evidence


def test_declined_and_failed():
    assert parse_call_response({"status": "DECLINED"}).status == "declined"
    assert parse_call_response({"status": "FAILED"}).status == "failed"


def test_unknown_status_normalises_instead_of_crashing():
    result = parse_call_response({"status": "CANCELED BY CALLER"})
    assert result.status == "canceled_by_caller"


def test_completed_with_everything_missing():
    result = parse_call_response({"run_id": "call_1", "status": "COMPLETED"})
    assert result.status == "completed"
    assert result.structured_result is None
    assert result.transcript is None
    assert result.completion_confidence is None
    assert result.task_completed is None
    assert result.evidence is None


def test_completion_confidence_as_bare_number_still_works():
    raw = {"status": "COMPLETED", "completion_confidence": 0.5}
    result = parse_call_response(raw)
    assert result.completion_confidence == 0.5


def test_empty_recipients_does_not_raise():
    result = parse_call_response({"status": "COMPLETED", "recipients": []})
    assert result.status == "completed"
    assert result.structured_result is None
    assert result.transcript is None


def test_top_level_structured_result_used_as_fallback():
    # Some call shapes (batch, or a future API version) may put the result
    # at the top level instead of under recipients[0] - fall back to it
    # rather than losing the data.
    raw = {
        "status": "COMPLETED",
        "structured_result": {"resolved": True},
        "recipients": [],
    }
    result = parse_call_response(raw)
    assert result.structured_result == {"resolved": True}


def test_next_step_poll_after_seconds_is_honoured():
    result = parse_call_response(
        {"status": "PREPARING", "next_step": {"poll_after_seconds": 2}}
    )
    assert result.poll_after_seconds == 2.0


def test_poll_after_seconds_clamped_to_at_least_one():
    result = parse_call_response(
        {"status": "PREPARING", "next_step": {"poll_after_seconds": 0}}
    )
    assert result.poll_after_seconds == 1.0


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
