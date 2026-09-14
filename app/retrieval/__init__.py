"""Pre-call retrieval: grounds the task string in real KB documents instead
of an agent's memory. Retrieval happens once, before dispatch — CALL-E has
no hook to query anything mid-call — so the briefing has to be generous (a
handful of chunks) and honest about gaps (below threshold means "say you
don't know," not "guess").

Two framings, same search underneath:

- build_briefing() — primary. Used when there's no student record to
  answer from (the "other" intent, or a record-backed intent with no
  student number). The reference material IS the answer.
- build_supplementary_briefing() — secondary. Used alongside a student
  record (proof_of_registration / subject_cancellation). The record is
  the answer for anything it covers; this is background for anything it
  doesn't — e.g. a proof-of-registration caller who also asks *where* the
  Cashier's Office is, which lives in fees-and-payment.md, not their
  record. The record always wins if the two ever disagree.
"""

import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import List, Tuple

from .base import Hit, Retriever
from .chunker import Chunk, chunk_file, chunk_pdf
from .tfidf import INDEX_DIR, TfidfRetriever

logger = logging.getLogger(__name__)

# Tuned against scripts/tune_threshold.py on the eleven-file nust KB: known
# in-scope queries scored 0.137-0.209, known out-of-scope scored 0.000-0.075.
# 0.13 sits in that gap with a small safety margin on the low end - a prior
# pass here left only 0.002 of margin on "how much are the fees this
# semester", which a single future KB edit could tip over. Re-run the
# tuning script and adjust this after any real change to the KB's size,
# content, or tokenizer - and treat it as a real check, not a formality:
# adding "opens"/"starts" phrasing to the registration-dates section (so
# "when does registration start" would match) pushed "is the cafeteria
# open today" up purely by sharing the word "open" - fixing one paraphrase
# gap opened another. See _LOW_RELEVANCE_PDF_STEMS below for the same
# lesson from PDF ingestion.
TFIDF_MIN_SCORE = 0.13

KB_ROOT = Path(__file__).resolve().parent.parent.parent / "kb"

# These PDFs are already hand-curated into cleaner, focused .md files
# (faculty-officers.md; academic-calendar-2026.md + public-holidays-2026.md)
# with none of the repeated page-header boilerplate raw PDF text carries.
# Auto-ingesting them too would duplicate that content at lower quality and
# dilute retrieval, so they're skipped by stem. Every other PDF dropped
# into a tenant's kb folder - including partial overlaps like the 2026
# prospective-students guide, most of which isn't curated anywhere - is
# ingested automatically.
_SUPERSEDED_PDF_STEMS = {
    "Faculty_Officers_Info",
    "2025-INSTITUTIONAL-CALENDAR-08JULY2025",
    "2025 INSTITUTIONAL CALENDAR APPROVED BY SENATE 13 NOV 2024",
    # Its admission-points section is already in admission-points.md, and its
    # satellite-campus pages (Eenhana/Lüderitz/Rietfontein, each repeating
    # "Campus" the same way the original faculty-officers.md bug did) measurably
    # broke an out-of-scope query on ingestion - already-curated content plus a
    # confirmed-harmful remainder, not a case worth keeping in raw form.
    "2026-Final-Guide-to-Prospective-Students_1",
    # Fully curated into academic-calendar-2026.md + public-holidays-2026.md
    # once the current date moved into 2026 and the -2025 versions of those
    # files went stale. Same reasoning as the 2025 calendar PDFs above.
    "2026-INSTITUTIONAL-CALENDAR",
    # Curated into international-students-study-permit.md after a taxonomy
    # sweep found the model inventing visa/permit specifics from nothing -
    # this PDF was the one real source for that topic, sitting auto-ingested
    # but apparently not scoring well enough raw to ground the answer. Same
    # reasoning as the other superseded PDFs: keeping both would duplicate
    # the same content at lower quality and dilute retrieval.
    "Notice_International Students 2025_Study Permit",
}

# Measured, not assumed: these four faculty prospectuses alone produced
# 1003 of 1313 total chunks (module-by-module curriculum listings, dozens
# of pages each) and demonstrably broke retrieval on ingestion - a known-
# good query ("when does the semester actually start") dropped below
# TFIDF_MIN_SCORE, and known out-of-scope queries rose toward it, purely
# from the corpus-wide term-frequency shift. Detailed course curricula are
# also a poor match for what a 15-second phone intake actually asks.
# Excluded until there's a real need (and a better approach - per-course
# chunking, a higher k, or a separate lower-weighted index) rather than
# left in a state that's measured to be worse than not ingesting them.
_LOW_RELEVANCE_PDF_STEMS = {
    "FCI-Prospectus-2025",
    "FEBE-Prospectus-2025",
    "FHNRAS-Prospectus-2025",
    "HP-GSB-Prospectus-2025",
    # Measured too: 188 of this tenant's 241 total chunks (78%) and the top
    # offender pushing "where can i park on campus" back above threshold.
    # 84 pages of regulatory/policy text repeats "campus" densely across
    # many unrelated sections (network access, various site locations),
    # the same class of problem as the four prospectuses above, just at a
    # smaller scale that still moved the needle.
    "prospectus-2025-GENERAL-INFORMATION-AND-REGULATIONS",
    # Even at 26 pages, this one still measurably hurt retrieval - a
    # regional resource-centre directory page (contact-listing-dense, same
    # shape as the original faculty-officers.md bug) outscored genuinely
    # relevant chunks even after email/phone masking and a general
    # per-chunk token-frequency cap (see _MAX_TOKEN_REPEATS_PER_CHUNK in
    # tfidf.py). Every PDF in this KB has now independently reproduced
    # this pattern regardless of size - it's the content shape (directory
    # listings, repeated headers), not file size, that predicts risk.
    "Pocket-Guide-For-Flexible-Learning-1stSemester2025",
}


def _load_chunks(tenant_id: str) -> List[Chunk]:
    folder = KB_ROOT / tenant_id
    chunks: List[Chunk] = []
    if folder.exists():
        for md in sorted(folder.glob("*.md")):
            chunks.extend(chunk_file(md, tenant_id))
        for pdf in sorted(folder.rglob("*.pdf")):
            if pdf.stem in _SUPERSEDED_PDF_STEMS or pdf.stem in _LOW_RELEVANCE_PDF_STEMS:
                continue
            chunks.extend(chunk_pdf(pdf, tenant_id))
    return chunks


def _index_is_stale(tenant_id: str) -> bool:
    """True if any kb/<tenant>/*.md or */*.pdf file was edited after the
    index was last built — a stale pickle used to mean new KB content sat
    on disk, completely unsearchable, with nothing in code review or the
    app itself hinting that it wasn't wired in.
    """
    index_path = INDEX_DIR / f"{tenant_id}.pkl"
    if not index_path.exists():
        return True
    index_mtime = index_path.stat().st_mtime
    folder = KB_ROOT / tenant_id
    source_files = list(folder.glob("*.md")) + list(folder.rglob("*.pdf"))
    return any(f.stat().st_mtime > index_mtime for f in source_files)


@lru_cache
def get_retriever(tenant_id: str) -> Retriever:
    if not _index_is_stale(tenant_id):
        loaded = TfidfRetriever.load(tenant_id)
        if loaded is not None:
            logger.info(
                "retrieval: %s, %d chunks, index loaded from cache", tenant_id, len(loaded.chunks)
            )
            return loaded

    chunks = _load_chunks(tenant_id)
    retriever = TfidfRetriever()
    retriever.build(chunks)
    retriever.save(tenant_id)
    logger.info(
        "retrieval: %s, %d chunks, index built %s",
        tenant_id,
        len(chunks),
        time.strftime("%H:%M"),
    )
    return retriever


def _search(query: str, retriever: Retriever) -> Tuple[List[Hit], List[dict]]:
    hits = [h for h in retriever.search(query, k=4) if h.score >= TFIDF_MIN_SCORE]
    provenance = [
        {
            "chunk_id": h.chunk.id,
            "source": h.chunk.source,
            "heading": h.chunk.heading,
            "score": round(h.score, 3),
            "office": h.chunk.office,
        }
        for h in hits
    ]
    return hits, provenance


def _blocks(hits: List[Hit]) -> str:
    return "\n\n".join(f"[{h.chunk.heading}]\n{h.chunk.text}" for h in hits)


def build_briefing(
    query: str, retriever: Retriever, tenant: dict
) -> Tuple[str, List[dict], bool]:
    """Returns (briefing_text, provenance, no_kb_coverage). Below threshold
    means genuinely no coverage: empty briefing, empty provenance, True —
    the right outcome on a phone call is "I don't know" over a weak guess.
    """
    hits, provenance = _search(query, retriever)
    if not hits:
        return "", [], True

    briefing = (
        f"Reference information from official {tenant['short_name']} documents. "
        "You may use this to answer:\n"
        f"---\n{_blocks(hits)}\n---\n"
        "Answer only from this reference and the caller's own record. If the "
        "answer is not in the reference, say plainly that you don't have that "
        "information and that the right office will follow up. Never guess at "
        "dates, amounts, or requirements."
    )
    return briefing, provenance, False


def build_supplementary_briefing(
    query: str, retriever: Retriever, tenant: dict
) -> Tuple[str, List[dict], bool]:
    """Same search, background framing. No hit here is normal — it just
    means the record already covers the question — so the caller should
    treat a False/empty return as "nothing extra," not "coverage failed."
    """
    hits, provenance = _search(query, retriever)
    if not hits:
        return "", [], False

    briefing = (
        f"Additional background from official {tenant['short_name']} documents, in "
        "case they ask something their record doesn't cover:\n"
        f"---\n{_blocks(hits)}\n---\n"
        "Their record above always takes precedence over this if the two ever "
        "disagree. Do not use this to override or contradict what their record says."
    )
    return briefing, provenance, False
