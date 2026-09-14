"""Eagerly rebuild the TF-IDF index for a tenant's KB. get_retriever()
already rebuilds automatically once a kb/<tenant>/*.md file is newer than
the saved index, so this script is for forcing it ahead of that — before
tune_threshold.py, in CI, or to warm the cache right after an edit.

    python scripts/build_index.py nust
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval import _load_chunks  # noqa: E402
from app.retrieval.tfidf import TfidfRetriever  # noqa: E402


def build(tenant: str) -> None:
    chunks = _load_chunks(tenant)
    file_count = len(list((Path("kb") / tenant).glob("*.md")))
    print(f"{len(chunks)} chunks from {file_count} files")

    r = TfidfRetriever()
    r.build(chunks)
    r.save(tenant)
    print(f"index written to kb/.index/{tenant}.pkl")


if __name__ == "__main__":
    build(sys.argv[1] if len(sys.argv) > 1 else "nust")
