# Ringback — Retrieval Layer

Design and implementation for grounding calls in institutional documents.

---

## 1. The shape, and why

**Retrieval happens before the call, never during it.** CALL-E has no hook to query your system mid-conversation. So the flow is:

```
query arrives → classify → retrieve → write findings into the task string
              → CALL-E dials, already briefed
```

The agent's job is *preparing* the call, not participating in it. Everything the caller might need has to be in the task string before the phone rings.

**Two consequences that shape the whole design:**

1. **You can't retrieve reactively**, so retrieve generously — 3–5 chunks, not 1. A slightly over-briefed agent is fine; an under-briefed one has to say "I'll have someone follow up."
2. **A hallucination on a call is worse than in chat.** Nobody sees a citation, nobody scrolls back, the student acts on what they heard. So "I don't know, I'll have the right office follow up" must be an explicit success state in the schema, not a failure.

---

## 2. Start with TF-IDF, not embeddings

The obvious move is sentence-transformers. Don't, at least not first.

| | TF-IDF (scikit-learn) | Embeddings (sentence-transformers) |
|---|---|---|
| Install size | ~30 MB | ~2 GB (torch) |
| Setup time | seconds | a long download on a Namibian connection |
| Quality on a few hundred chunks | genuinely competitive | better on paraphrase |
| Offline | yes | yes, after download |

For a corpus of a few hundred chunks of institutional prose — where the caller's words and the document's words overlap heavily ("proof of registration", "drop a subject", "fee balance") — lexical matching does very well.

**Both sit behind one interface**, so swapping later is a one-line change. Build TF-IDF now, upgrade if there's spare bandwidth.

---

## 3. Document format

`kb/nust/*.md`, with frontmatter:

```markdown
---
title: Proof of registration
topic: proof_of_registration
office: registrar
---

## Who can request one
...
```

`office` matters — it's what the router uses when retrieval finds relevant material but the agent still can't resolve the query.

**On expanding the corpus:** the original six files fit in a prompt, so retrieval added machinery without adding knowledge until real NUST material was added — faculty officer contacts and confirmed 2025 calendar/holiday dates, sourced from the official institutional calendar and faculty officer PDFs in `kb/nust/NUST Staff Related Documents/` and `kb/nust/NUST Students Related Documents/`. Those source PDFs aren't ingested directly (the chunker only reads `*.md`); relevant material is hand-curated into frontmatter'd `.md` files in the same style as the rest of the KB, and low-value governance content (Council/Senate/committee meeting schedules, NCHE accreditation cycles) was deliberately left out — it's never something a student calls about. Re-run `scripts/build_index.py nust` and `scripts/tune_threshold.py nust` after any further change; TFIDF_MIN_SCORE was nudged from 0.09 to 0.095 when this corpus grew, since a 9-file corpus pushed one out-of-scope probe query just above the old threshold.

---

## 4–14. Implementation

See `app/retrieval/` for the chunker, base interface, TF-IDF retriever, index build script, and threshold, and `app/dispatcher.py` for `build_briefing()` integration. `tests/test_retrieval.py` covers known-query retrieval and the below-threshold no-coverage path.

Constraints followed:

- scikit-learn only. No sentence-transformers, torch, or vector database — `EmbeddingRetriever` is a documented future swap behind the same `Retriever` protocol, not built now.
- Nothing outside `app/retrieval/` imports `TfidfRetriever` directly; everything goes through the protocol.
- Below threshold → no reference block injected, case marked `no_kb_coverage`. Never inject a weak match.
- `get_retriever()` compares the newest `.md` mtime in `kb/<tenant>/` against the saved index's mtime and rebuilds automatically if the KB changed — a stale cached index used to mean new KB content sat on disk, completely unsearchable, with no signal anywhere that it wasn't wired in. `scripts/build_index.py` still exists for an eager, on-demand rebuild. Startup logs one line per tenant (`retrieval: nust, 18 chunks, index built 14:22` or `... index loaded from cache`) so an unexpectedly empty briefing on a call is fast to diagnose.
- The "Sources used" panel uses only existing shared components — no new hardcoded colors, fonts, radii or sizes.

---

## 15. Connecting your own data (future work, not built)

Three shapes, three different stories:

- **Documents** (prospectus, handbooks, fee schedules) → a folder to drop files into. Already how `kb/nust/` works; a `scripts/ingest.py` taking a folder of PDFs/markdown, chunking, writing frontmatter, and rebuilding the index would make this a one-command onboarding path rather than a web upload flow.
- **Student records** → `StudentDirectory` interface, with `PostgresDirectory` / `RESTDirectory` as documented future implementations.
- **Live systems** (Moodle, ITS) → a sync job, not a live query — a phone call can't block on a slow ITS instance.

A signup-and-upload UI is two to three weeks of auth, tenant isolation, and credential storage — invisible in a three-minute video, and it competes for the days the agentic escalation loop needs. `tenants/` with two files plus this documented interface makes the same claim honestly, today.
