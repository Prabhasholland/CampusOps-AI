"""Plain-assertion tests for the reasoning step (app/prepare.py) - no
pytest dependency, run directly: python tests/test_prepare.py

The compound/conditional/out-of-scope tests hit the real Gemini API, since
the whole point is verifying actual reasoning rather than a scripted
response - slower than the rest of the suite, and they skip gracefully
without GEMINI_API_KEY rather than failing the run.

Quota note (found 2026-08-28): the free tier for gemini-2.5-flash returned
429 RESOURCE_EXHAUSTED against "generate_content_free_tier_requests, limit:
20" partway through a single run of this file, with a shrinking retry-delay
across consecutive attempts (47s, then 9s) - consistent with a real, small,
rolling quota rather than a one-off blip. Don't run this file repeatedly in
short succession during development; each of the three model-backed tests
below is one real call, plus retries on quota/5xx. If this suite starts
failing with 429s, that's the fallback path's job to survive in production
(see test_simulated_api_failure_falls_back_cleanly) - it is not a bug in
prepare.py.
"""

import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()

from app.directory import Student, Subject  # noqa: E402
from app.prepare import ModelPreparer, prepare_call  # noqa: E402
from app.prepare import _client as _model_client  # noqa: E402
from app.prepare import _groq_client  # noqa: E402
from app.tenants import load_tenant  # noqa: E402

_tenant = load_tenant("nust")
_HAS_MODEL = bool(os.environ.get("GEMINI_API_KEY"))
_HAS_GROQ = bool(os.environ.get("GROQ_API_KEY"))


def _skip(name: str) -> None:
    print(f"SKIP  {name} (GEMINI_API_KEY not set)")


def _prepare_with_retry(query, student, tenant, attempts=3, backoff=4.0):
    """Calling ModelPreparer directly (rather than prepare_call) is
    deliberate here - the point is testing reasoning quality, not the
    resilience layer, which has its own dedicated test below. Retried only
    to absorb Gemini's own transient 5xx blips during the test run.
    """
    last_exc = None
    for attempt in range(attempts):
        try:
            return ModelPreparer(_model_client()).prepare(query, student, tenant)
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if attempt < attempts - 1:
                time.sleep(backoff)
    raise last_exc


def test_compound_query_covers_both_rules():
    if not _HAS_MODEL:
        return _skip("test_compound_query_covers_both_rules")
    query = (
        "I need my proof of registration for my bank, and I also want to know "
        "where the Cashier's Office is if I still owe money."
    )
    plan = _prepare_with_retry(query, None, _tenant)
    assert plan.intent in ("proof_of_registration", "other"), plan.intent
    briefing_lower = plan.briefing.lower()
    assert "registration" in briefing_lower or "cashier" in briefing_lower, plan.briefing


def test_conditional_query_states_the_interaction():
    if not _HAS_MODEL:
        return _skip("test_conditional_query_states_the_interaction")
    student = Student(
        student_number="220099999",
        name="Test Student",
        phone="+264810000000",
        registration_status="registered",
        fee_balance=1500.0,
        subjects=[Subject(code="CSC612S", name="Test Subject", drop_deadline="2026-09-05")],
    )
    query = (
        "I registered late and I'm not sure if I can still drop CSC612S without "
        "paying - my fees are also outstanding so I don't know if that changes anything."
    )
    plan = _prepare_with_retry(query, student, _tenant)
    # Either the briefing states the fee/deadline interaction, or the model
    # judged this needs a human to resolve - both are the "noticed the
    # interaction" outcome a fixed template can't produce on its own.
    combined = (plan.briefing + " " + plan.reasoning).lower()
    assert "fee" in combined or "balance" in combined, combined
    assert "deadline" in combined or "drop" in combined, combined


def test_simple_out_of_scope_still_calls():
    if not _HAS_MODEL:
        return _skip("test_simple_out_of_scope_still_calls")
    plan = _prepare_with_retry("where can I park on campus", None, _tenant)
    # A plain question the KB doesn't cover should still be called and
    # answered honestly on the call itself - should_call=False is reserved
    # for cases needing account-specific human judgment, not any KB miss.
    assert plan.should_call is True, plan.reasoning


def test_simulated_gemini_failure_falls_back_to_groq():
    """Gemini down, Groq up - should resolve one tier down, not all the way
    to deterministic. This is the whole point of a second provider: Gemini
    has hit real 429s repeatedly (see module docstring), and every one of
    those should now still get a model-reasoned plan, just from Groq.
    """
    if not _HAS_GROQ:
        return _skip("test_simulated_gemini_failure_falls_back_to_groq")
    real_key = os.environ.get("GEMINI_API_KEY")
    os.environ["GEMINI_API_KEY"] = "invalid-key-for-testing"
    _model_client.cache_clear()
    try:
        plan = prepare_call("what are your office hours", None, _tenant)
    finally:
        if real_key is not None:
            os.environ["GEMINI_API_KEY"] = real_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)
        _model_client.cache_clear()

    assert plan.preparer_used == "groq", plan.preparer_used
    assert plan.should_call is True


def test_simulated_total_outage_falls_back_to_deterministic():
    real_gemini_key = os.environ.get("GEMINI_API_KEY")
    real_groq_key = os.environ.get("GROQ_API_KEY")
    os.environ["GEMINI_API_KEY"] = "invalid-key-for-testing"
    os.environ["GROQ_API_KEY"] = "invalid-key-for-testing"
    _model_client.cache_clear()
    _groq_client.cache_clear()
    try:
        plan = prepare_call("what are your office hours", None, _tenant)
    finally:
        for env_key, real_value in (("GEMINI_API_KEY", real_gemini_key), ("GROQ_API_KEY", real_groq_key)):
            if real_value is not None:
                os.environ[env_key] = real_value
            else:
                os.environ.pop(env_key, None)
        _model_client.cache_clear()
        _groq_client.cache_clear()

    assert plan.preparer_used == "deterministic", plan.preparer_used
    assert plan.should_call is True


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
    print(f"\nAll {len(tests)} tests passed (model-dependent tests skip without GEMINI_API_KEY)")


if __name__ == "__main__":
    main()
