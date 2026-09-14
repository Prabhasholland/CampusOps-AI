"""Print retrieval scores for known in-scope and out-of-scope queries, to
help pick TFIDF_MIN_SCORE in app/retrieval/__init__.py. Run after any KB
change.

    python scripts/tune_threshold.py nust
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval import _load_chunks  # noqa: E402
from app.retrieval.tfidf import TfidfRetriever  # noqa: E402

CASES = [
    ("i need my proof of registration for my bank", True),
    ("can i still drop CSC612S", True),
    ("what are the admission requirements for engineering", True),
    ("when does the semester actually start", True),
    ("how much are the fees this semester", True),
    ("where can i park on campus", False),
    ("my laptop broke", False),
    ("is the cafeteria open today", False),
]


def main(tenant: str) -> None:
    retriever = TfidfRetriever()
    retriever.build(_load_chunks(tenant))

    print(f"{'query':<55} {'expected':<10} top score")
    print("-" * 80)
    for query, expected_in_scope in CASES:
        hits = retriever.search(query, k=1)
        score = hits[0].score if hits else 0.0
        label = "in-scope" if expected_in_scope else "out-of-scope"
        print(f"{query:<55} {label:<12} {score:.3f}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "nust")
