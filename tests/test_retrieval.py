"""Plain-assertion tests for the retrieval layer — no pytest dependency.

Run directly: python tests/test_retrieval.py

The no-coverage test is the one that matters most: it's the guard against
a confidently wrong answer on a live call.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval import TFIDF_MIN_SCORE, _load_chunks, build_briefing  # noqa: E402
from app.retrieval.tfidf import TfidfRetriever  # noqa: E402
from app.tenants import load_tenant  # noqa: E402

_retriever = TfidfRetriever()
_retriever.build(_load_chunks("nust"))
_tenant = load_tenant("nust")


def test_known_queries_retrieve_expected_topic():
    cases = [
        ("i need my proof of registration for my bank", "proof_of_registration"),
        ("can i still drop a subject", "subject_cancellation"),
        ("how much are the fees this semester", "fees_and_payment"),
    ]
    for query, expected_topic in cases:
        hits = _retriever.search(query, k=1)
        assert hits, query
        assert hits[0].chunk.topic == expected_topic, (query, hits[0].chunk.topic)


def test_out_of_scope_query_falls_below_threshold():
    hits = _retriever.search("my laptop broke", k=1)
    assert not hits or hits[0].score < TFIDF_MIN_SCORE


def test_briefing_empty_when_no_coverage():
    briefing, sources, no_coverage = build_briefing("my laptop broke", _retriever, _tenant)
    assert briefing == ""
    assert sources == []
    assert no_coverage is True


def test_briefing_present_when_in_scope():
    briefing, sources, no_coverage = build_briefing(
        "i need my proof of registration", _retriever, _tenant
    )
    assert briefing != ""
    assert len(sources) > 0
    assert no_coverage is False
    assert all({"chunk_id", "source", "heading", "score", "office"} <= s.keys() for s in sources)


def test_briefing_never_exceeds_four_sources():
    briefing, sources, _ = build_briefing(
        "proof of registration fees subject cancellation admission", _retriever, _tenant
    )
    assert len(sources) <= 4


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
