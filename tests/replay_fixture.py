"""Replay a saved CALL-E get_call_run response through Ringback's own parsing
and schema validation, without spending a real call.

Usage:
    python tests/replay_fixture.py tests/fixtures/happy_path_proof_of_reg.json proof_of_registration
    python tests/replay_fixture.py tests/fixtures/voicemail.json subject_cancellation

Intent must be one of: proof_of_registration, subject_cancellation, other
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.calle_client import parse_call_response  # noqa: E402
from app.schemas import PROOF_OF_REG, SUBJECT_CANCELLATION, TRIAGE  # noqa: E402

SCHEMAS = {
    "proof_of_registration": PROOF_OF_REG,
    "subject_cancellation": SUBJECT_CANCELLATION,
    "other": TRIAGE,
}


def check_against_schema(structured: dict, schema: dict) -> list:
    problems = []
    for field in schema.get("required", []):
        if field not in structured:
            problems.append(f"missing required field: {field}")
    for field, spec in schema.get("properties", {}).items():
        if field in structured and "enum" in spec and structured[field] not in spec["enum"]:
            problems.append(
                f"{field}={structured[field]!r} is not in the defined enum {spec['enum']}"
            )
    return problems


def main() -> None:
    if len(sys.argv) != 3:
        print(f"Usage: python {sys.argv[0]} <fixture.json> <intent>")
        print(f"  intent: one of {', '.join(SCHEMAS)}")
        raise SystemExit(1)

    fixture_path, intent = sys.argv[1], sys.argv[2]
    schema = SCHEMAS.get(intent)
    if schema is None:
        print(f"Unknown intent {intent!r}. Choose from {', '.join(SCHEMAS)}")
        raise SystemExit(1)

    raw = json.loads(Path(fixture_path).read_text(encoding="utf-8"))
    result = parse_call_response(raw)

    print(f"status:                {result.status}")
    print(f"task_completed:        {result.task_completed}")
    print(f"completion_confidence: {result.completion_confidence}")
    print(f"transcript lines:      {len((result.transcript or '').splitlines())}")
    print(f"structured_result:     {json.dumps(result.structured_result, indent=2)}")

    if result.status != "completed":
        print(
            f"\nNot a completed call ({result.status}) - the dispatcher would "
            f"increment call_attempts and dispatch a new call, or mark the case "
            f"'failed' if this was attempt 3."
        )
        return

    structured = result.structured_result
    if not isinstance(structured, dict):
        print(
            "\nstructured_result is not a dict - the dispatcher's hardening "
            "coerces this to {} and routes the case rather than crashing."
        )
        structured = {}

    problems = check_against_schema(structured, schema)
    if problems:
        print("\nSchema problems found:")
        for p in problems:
            print(f"  - {p}")
    else:
        print("\nSchema check passed: every required field present, every enum value defined.")

    if structured.get("resolved") is True:
        print("Dispatcher outcome: case.status -> 'resolved'")
    else:
        print("Dispatcher outcome: case.status -> 'routed' (route_case would run)")


if __name__ == "__main__":
    main()
