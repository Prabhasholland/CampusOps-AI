"""prepare_call(): the one reasoning step in Ringback.

Reads the caller's raw query and, if known, their record. Decides the
intent, decides what to look up, judges whether what came back actually
answers the question - including how a KB rule and the student's own
record interact (a fee balance can block a subject drop regardless of the
deadline) - and produces a CallPlan: intent, a briefing written in its own
words, and whether the case should be dialled at all or routed straight to
a person instead.

CALL-E is still the only thing reasoning *during* a call. Nothing here
talks to CALL-E, and nothing runs once dispatch happens - this is a single
pre-call step, same as the retrieval-only version it replaces. Behind a
Preparer protocol so a model outage, timeout, or rate limit degrades to
DeterministicPreparer (the original keyword classifier + single-pass
TF-IDF) rather than failing the case.
"""

import datetime
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from functools import lru_cache
from typing import List, Optional, Protocol

from google import genai
from google.genai import types
from groq import Groq, RateLimitError as GroqRateLimitError

from .classifier import classify
from .directory import Student, format_currency
from .retrieval import _blocks, _search, build_briefing, build_supplementary_briefing, get_retriever

logger = logging.getLogger(__name__)

# gemini-2.5-flash's free tier is 20 requests/day and 5/minute - verified
# empirically (the 429 body states the exact quotaValue), not assumed.
# That's unworkable for development or a live demo. Quota is scoped
# per-model (confirmed the same way), so a different model has separate,
# unexhausted quota. gemini-2.5-flash-lite and gemini-2.0-flash - both
# named in earlier advice - are already 404 for this key ("no longer
# available to new users"); gemini-3.5-flash-lite is the current
# equivalent and works today. Pinned to an explicit version rather than
# the "-latest" alias, since an alias can change behavior out from under
# a near-final demo without any code change to notice.
MODEL_NAME = "gemini-3.5-flash-lite"

# Groq's free tier is a separate failure domain from Gemini's - a Google
# quota surprise or outage doesn't take this down too. Not one of Groq's
# "compound"/"compound-mini" models - those do their own web search and code
# execution mid-answer, which is exactly the wrong thing here: this step
# reasons over the KB and the record, not the open internet. llama-3.3-70b-
# versatile (the model named in earlier advice) is 404 "does not exist" for
# this key - verified via client.models.list(), not assumed - Groq's free
# lineup had already rotated past it by the time this was wired up.
# openai/gpt-oss-120b is what's actually available today with solid
# reasoning and OpenAI-style tool calling.
# search_kb calls and the final submit_plan call share this same budget - a
# model that spends all of it on searches (seen in testing: 4 straight
# search_kb calls with steadily less relevant phrasing, on a question the KB
# genuinely doesn't cover) never gets to submit_plan at all and that attempt
# errors out. Cut to 2 deliberately, for latency - most queries resolve on
# the first search, and each iteration is a full round-trip. This makes
# hitting the ceiling on a genuinely compound question more likely, not
# less; that's accepted, not overlooked, because prepare_call() already
# retries and fails over across two providers before ever reaching
# DeterministicPreparer - non-convergence here degrades gracefully to a
# working answer, it does not fail the case.
GROQ_MODEL_NAME = "openai/gpt-oss-120b"
MAX_ITERATIONS = 2
_MODEL_ATTEMPTS = 2
_MODEL_BACKOFF_SECONDS = 1.5

INTENTS = ("proof_of_registration", "subject_cancellation", "other")
CATEGORIES = (
    "fees",
    "academic_records",
    "faculty",
    "accommodation",
    "exams",
    "it_support",
    "unclear",
)


@dataclass
class CallPlan:
    intent: str
    reasoning: str
    briefing: str
    should_call: bool
    preparer_used: str  # "gemini" | "groq" | "deterministic"
    category: Optional[str] = None  # only meaningful when intent == "other"
    route_to: Optional[str] = None  # tenant office key, required when should_call is False
    sources_used: List[dict] = field(default_factory=list)
    confidence: str = "medium"  # low | medium | high


class Preparer(Protocol):
    def prepare(self, query: str, student: Optional[Student], tenant: dict) -> CallPlan: ...


class DeterministicPreparer:
    """The original pipeline, unchanged in behavior: keyword classify plus
    single-pass TF-IDF retrieval. This is the fallback, so it must never
    itself raise in a way that blocks dispatch, and it never routes without
    calling - that judgment call belongs to the model; the deterministic
    path always dials, same as before this reasoning step existed.
    """

    def prepare(self, query: str, student: Optional[Student], tenant: dict) -> CallPlan:
        classification = classify(query)
        retriever = get_retriever(tenant["id"])
        record_backed = classification.intent in (
            "proof_of_registration",
            "subject_cancellation",
        ) and student is not None

        if record_backed:
            briefing, sources, _ = build_supplementary_briefing(query, retriever, tenant)
        else:
            briefing, sources, _ = build_briefing(query, retriever, tenant)

        return CallPlan(
            intent=classification.intent,
            category=classification.category,
            reasoning="Deterministic fallback: keyword-matched intent, single-pass retrieval.",
            briefing=briefing,
            should_call=True,
            route_to=None,
            sources_used=sources,
            confidence="medium" if classification.confidence >= 0.7 else "low",
            preparer_used="deterministic",
        )


def _search_kb_spec() -> dict:
    return {
        "name": "search_kb",
        "description": (
            "Search the official knowledge base for passages relevant to a query. "
            "Call this one to three times with different phrasing if the first pass "
            "doesn't cover every part of a compound question."
        ),
        "parameters": {
            "type": "object",
            "properties": {"query_text": {"type": "string", "description": "Search phrase."}},
            "required": ["query_text"],
        },
    }


def _submit_plan_spec(offices: dict) -> dict:
    office_keys = list(offices.keys())
    office_purposes = "; ".join(
        f"{key} ({o.get('handles', o['name'])})" for key, o in offices.items()
    )
    return {
        "name": "submit_plan",
        "description": "Submit your final call plan. Call this exactly once, when ready.",
        "parameters": {
            "type": "object",
            "properties": {
                "intent": {"type": "string", "enum": list(INTENTS)},
                "category": {
                    "type": "string",
                    "enum": list(CATEGORIES),
                    "description": "Only meaningful when intent is 'other'.",
                },
                "reasoning": {
                    "type": "string",
                    "description": (
                        "Short note on what you worked out and why - especially any "
                        "interaction between a KB rule and this caller's own record, "
                        "or why nothing in either covers the question."
                    ),
                },
                "briefing": {
                    "type": "string",
                    "description": (
                        "The paragraph that gets read into the call task, in your own "
                        "words - never pasted chunks. Ground it only in what search_kb "
                        "returned and the caller's own record. Never invent a date, "
                        "amount, or requirement that isn't in one of those two places. "
                        "If something isn't covered, say so plainly rather than guessing. "
                        "If should_call is false, nobody's identity has been confirmed and "
                        "this call is not happening - this field must not state any "
                        "balance, mark, date, or other record detail; write one short "
                        "internal note on why it's being routed instead."
                    ),
                },
                "should_call": {
                    "type": "boolean",
                    "description": (
                        "False only when this needs a human who can see the account "
                        "directly - route it instead of spending a call on it."
                    ),
                },
                "route_to": {
                    "type": "string",
                    "enum": office_keys,
                    "description": f"Required when should_call is false. What each office "
                    f"actually handles: {office_purposes}.",
                },
                "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            },
            "required": ["intent", "reasoning", "briefing", "should_call", "confidence"],
        },
    }


# The same plain-dict specs, adapted at the point of use to each SDK's tool
# shape - google-genai wants a FunctionDeclaration, Groq (OpenAI-compatible)
# wants {"type": "function", "function": {...}}. One prompt, one pair of
# specs, one output parser (_parse_submit_plan_args below); providers differ
# only in the client and how the tool call comes back.
_SEARCH_KB_DECL = types.FunctionDeclaration(**_search_kb_spec())


def _submit_plan_decl(offices: dict) -> types.FunctionDeclaration:
    return types.FunctionDeclaration(**_submit_plan_spec(offices))


def _groq_tools(offices: dict) -> list:
    return [
        {"type": "function", "function": _search_kb_spec()},
        {"type": "function", "function": _submit_plan_spec(offices)},
    ]


# Fields the disclosure rules say must never be spoken to anyone, or used to
# confirm identity only - not reasoned about or repeated in a briefing. Scrubbed
# from the model's input entirely rather than merely prompted against, so a
# leak (e.g. an invented honorific inferred from gender) can't happen even if
# the model ignores an instruction. See _disclosure_and_channel_instructions()
# in dispatcher.py for the parallel rule enforced during the call itself.
_NEVER_DISCLOSED_FIELDS = {"gender", "marital_status", "disability", "id_number", "birthdate"}

# Keys anywhere in the student record whose value is money, so every amount
# reaches the model already formatted - the model is not asked to format
# currency itself, only to use the string it's given.
_CURRENCY_FIELDS = {
    "fee_balance", "quote_total", "debit", "credit", "balance", "awarded",
    "allocated", "unallocated", "days_160", "days_90", "days_60", "days_30",
    "current", "future",
}

# Internal column names that read fine in a database and badly out loud
# ("your att_proj is 42.0%" - a real leak seen in testing). Relabelled to
# plain language before the model ever sees the key, rather than trusting
# an instruction not to repeat a raw field name back verbatim.
_FIELD_RELABELS = {
    "att_proj": "attendance_or_project_mark_percent",
    "wrs_score": "weighted_result_score",
    "prac_group": "practical_group",
    "tut_group": "tutorial_group",
    "date_of_balance": "balance_as_of_date",
    "days_160": "overdue_150_plus_days",
    "days_90": "overdue_90_to_149_days",
    "days_60": "overdue_60_to_89_days",
    "days_30": "overdue_30_to_59_days",
    "current": "current_period_amount",
    "future": "not_yet_due_amount",
    "is_nsfas": "is_government_bursary",
}


# Instruction alone doesn't reliably stop this - retested three times and
# the model still occasionally opens with the caller's own name ("Hello
# Petrina Uushona,"), which reads as a third party being briefed about the
# caller rather than the caller being spoken to directly. Full name can't be
# scrubbed from the model's input the way _NEVER_DISCLOSED_FIELDS is (CALL-E
# needs it for the identity-confirmation step in build_task()), so this
# strips just a leading name-greeting from the briefing after the fact.
def _strip_name_greeting(briefing: str, full_name: Optional[str]) -> str:
    if not full_name:
        return briefing
    pattern = re.compile(
        rf"^(?:hello|hi|hey)\s*,?\s*{re.escape(full_name)}\s*[.,!]?\s*",
        re.IGNORECASE,
    )
    stripped = pattern.sub("", briefing).strip()
    return stripped[:1].upper() + stripped[1:] if stripped else stripped


def _sanitize_for_model(value):
    if isinstance(value, dict):
        out = {}
        for k, v in value.items():
            if k in _NEVER_DISCLOSED_FIELDS:
                continue
            key = _FIELD_RELABELS.get(k, k)
            if k in _CURRENCY_FIELDS and isinstance(v, (int, float)):
                out[key] = format_currency(v)
            else:
                out[key] = _sanitize_for_model(v)
        return out
    if isinstance(value, list):
        return [_sanitize_for_model(v) for v in value]
    return value


def _system_instruction(query: str, student: Optional[Student], tenant: dict, office_keys: List[str]) -> str:
    if student:
        sanitized = _sanitize_for_model(student.model_dump(mode="json"))
        record_text = json.dumps(sanitized, indent=2, default=str)
    else:
        record_text = "No student record - caller has not provided a student number, or none matched."
    today = datetime.date.today().isoformat()
    office_purposes = "; ".join(
        f"{key} ({o.get('handles', o['name'])})" for key, o in tenant["offices"].items()
    )
    return (
        f"You are the reasoning step for {tenant['short_name']}'s callback system, "
        f"{tenant['calling_office']}. A student submitted a question through an intake "
        "form; nobody has spoken to them yet. You are NOT answering them yourself - you "
        "are preparing a briefing for a separate calling agent (CALL-E) that will phone "
        "them shortly. You never speak to the caller.\n\n"
        f"Today's date is {today}. Use it to judge whether any deadline in the record or "
        "the knowledge base has already passed - never just recite a deadline, say "
        "explicitly whether it's still open or has passed.\n\n"
        f"Valid intents: {', '.join(INTENTS)}.\n\n"
        "Work out what the caller actually needs, including how a KB rule and their own "
        "record interact if both apply (e.g. a fee balance can block a subject drop "
        "regardless of the deadline). You have exactly two tool calls total, searching "
        "and submitting combined - never search twice, that leaves nothing to submit "
        "with and the whole case fails. If you need to look something up, search "
        "once - phrase that one search as well as you can, covering both parts of a "
        "compound question if there are two - then call submit_plan on your next turn "
        "no matter what came back, even empty or partial. If you're already confident "
        "without searching, call submit_plan immediately on your first turn instead.\n\n"
        "Set should_call to false only for one of these specific reasons, nothing else: "
        "it needs someone to see the account directly, needs in-person identity "
        "verification (only when the question is about that specific caller's own "
        "account - a balance, a mark, a personal detail - and there's no record to "
        "confirm it against; a caller who simply hasn't given a student number for a "
        "general question is NOT this - most general questions never needed one at all, "
        "and 'no record was found' by itself is never a reason to route), or is one of "
        "- a caller who is not the student themselves, a "
        "payment arrangement, appeal, deferral, registration cancellation (withdrawing "
        "from the university entirely - distinct from dropping a single subject, which is "
        "the subject_cancellation intent and can be discussed on the call), name/ID "
        "correction, student number recovery, transcript request, disability "
        "accommodation, contact detail change, a complaint, a disciplinary/legal/medical "
        "matter, visa/study permit/immigration status (rules are jurisdiction-specific, "
        "change without notice, and are never in this KB - always route these to a "
        "person, regardless of how confident an answer might sound), or genuine distress "
        "needing a person. If none of these apply, should_call "
        "stays true - this includes the knowledge base simply having nothing on the "
        "topic, which by itself is NEVER a reason to route: CALL-E will listen, say "
        "honestly that nothing covers it, and report the case unresolved so the right "
        "office follows up afterward. Only once you've decided should_call is false for "
        "one of the specific reasons above do you also pick route_to, by what the office "
        f"actually handles, not just its name: {office_purposes}. Otherwise write the "
        "briefing paragraph yourself, grounded only in what search_kb returned and the "
        "record below - never "
        "invent a date, amount, or requirement that isn't in one of those two places. "
        "Never state how long a process will take - not '24 hours', not 'one to two "
        "weeks', not any number of days/hours/weeks - even if it sounds plausible. "
        "Always say the relevant office will confirm the timing instead. No exceptions to "
        "this one, regardless of what search_kb returns.\n\n"
        "Write the briefing in second person, addressed directly TO the caller, as if you "
        "were speaking straight to them - 'you'/'your' always means the caller, never "
        "CALL-E, never you (the model). Never write about the caller in the third person "
        "('the student', 'they', their name plus title, or their name at all) - the "
        "caller already knows who they are. Any currency amount you use is already "
        "formatted in the record below (e.g. "
        "\"N$2,340.00\") - copy it exactly, never reformat or recompute it. Never invent "
        "an honorific, gender, or title for the caller - fields that would reveal those "
        "have been deliberately withheld from you, so refer to them only by name or "
        "'you'.\n\n"
        "This gets read aloud, not displayed - write it the way a person would say it "
        "out loud. Never say 'knowledge base', 'record', 'database', 'field', or any "
        "other internal system term. Never repeat a raw field name from the record "
        "below (e.g. say 'your attendance mark', never 'att_proj'; say 'still open' or "
        "'has passed', never 'drop_deadline') - describe what it means, not what it's "
        "called.\n\n"
        "Before calling submit_plan, check the briefing you've written one more time: "
        "every amount and date in it must be traceable to a specific line in search_kb's "
        "results or the record below, and it must contain no statement of how long "
        "anything takes (no '24 hours', no '1-2 weeks', no day/week/hour count at all).\n\n"
        f'Caller\'s exact words: "{query}"\n\n'
        f"Caller's record:\n{record_text}\n\n"
        "When ready, call submit_plan exactly once."
    )


def _build_plan_from_args(
    args: dict, student: Optional[Student], chunks_seen: dict, preparer_used: str
) -> CallPlan:
    """Shared by every model-backed Preparer, so the name-greeting guard and
    the rest of the submit_plan parsing exist in exactly one place - a fix
    made here (like _strip_name_greeting) covers every provider, not just
    whichever one happened to be under test when the bug was found.
    """
    return CallPlan(
        intent=args["intent"],
        category=args.get("category"),
        reasoning=args["reasoning"],
        briefing=_strip_name_greeting(args["briefing"], student.name if student else None),
        should_call=args["should_call"],
        route_to=args.get("route_to"),
        sources_used=list(chunks_seen.values()),
        confidence=args.get("confidence", "medium"),
        preparer_used=preparer_used,
    )


class ModelPreparer:
    """Gemini, via google-genai's native function-calling."""

    def __init__(self, client: genai.Client, model: str = MODEL_NAME):
        self._client = client
        self._model = model

    def prepare(self, query: str, student: Optional[Student], tenant: dict) -> CallPlan:
        retriever = get_retriever(tenant["id"])
        office_keys = list(tenant["offices"].keys())
        tools = [types.Tool(function_declarations=[_SEARCH_KB_DECL, _submit_plan_decl(tenant["offices"])])]
        # Low, not zero - the should_call/route_to decision benefits from
        # consistency (seen flip-flopping on the exact same out-of-scope
        # query across otherwise-identical runs at the default temperature),
        # but the briefing is still meant to read as written in the model's
        # own words, not a canned template.
        config = types.GenerateContentConfig(tools=tools, temperature=0.2)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part(text=_system_instruction(query, student, tenant, office_keys))],
            )
        ]
        chunks_seen: dict = {}

        for _ in range(MAX_ITERATIONS):
            resp = self._client.models.generate_content(model=self._model, contents=contents, config=config)
            candidate = resp.candidates[0] if resp.candidates else None
            part = candidate.content.parts[0] if candidate and candidate.content.parts else None
            call = part.function_call if part else None

            if call is None:
                raise RuntimeError("Model responded without calling a tool.")

            contents.append(candidate.content)
            args = dict(call.args)

            if call.name == "submit_plan":
                return _build_plan_from_args(args, student, chunks_seen, "gemini")

            if call.name == "search_kb":
                hits, provenance = _search(args.get("query_text", query), retriever)
                for p in provenance:
                    chunks_seen[p["chunk_id"]] = p
                result_text = _blocks(hits) if hits else "No results above the relevance threshold."
                contents.append(
                    types.Content(
                        role="user",
                        parts=[
                            types.Part(
                                function_response=types.FunctionResponse(
                                    name="search_kb", response={"result": result_text}
                                )
                            )
                        ],
                    )
                )
                continue

            raise RuntimeError(f"Model called unknown tool: {call.name}")

        raise RuntimeError("Model did not converge on a plan within the iteration budget.")


class GroqPreparer:
    """Same prompt, same specs, same output shape as ModelPreparer - only the
    client and the OpenAI-style tool-call wire format differ. Exists so a
    Gemini quota exhaustion (hit repeatedly even on the smaller model - see
    MODEL_NAME comment) has an independent second provider to fall through
    to before ever touching DeterministicPreparer.
    """

    def __init__(self, client, model: str = GROQ_MODEL_NAME):
        self._client = client
        self._model = model

    def prepare(self, query: str, student: Optional[Student], tenant: dict) -> CallPlan:
        retriever = get_retriever(tenant["id"])
        office_keys = list(tenant["offices"].keys())
        tools = _groq_tools(tenant["offices"])
        messages = [{"role": "system", "content": _system_instruction(query, student, tenant, office_keys)}]
        chunks_seen: dict = {}

        for _ in range(MAX_ITERATIONS):
            resp = self._client.chat.completions.create(
                model=self._model, messages=messages, tools=tools, tool_choice="auto", temperature=0.2
            )
            message = resp.choices[0].message
            tool_calls = message.tool_calls

            if not tool_calls:
                raise RuntimeError("Model responded without calling a tool.")

            # Re-sending message.model_dump() verbatim 400s - the response
            # carries extra fields (e.g. "annotations") this same API
            # rejects as input. Round-trip only the fields a tool-call turn
            # actually needs.
            messages.append(
                {
                    "role": "assistant",
                    "content": message.content,
                    "tool_calls": [
                        {
                            "id": tc.id,
                            "type": "function",
                            "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                        }
                        for tc in tool_calls
                    ],
                }
            )

            for tc in tool_calls:
                args = json.loads(tc.function.arguments)

                if tc.function.name == "submit_plan":
                    return _build_plan_from_args(args, student, chunks_seen, "groq")

                if tc.function.name == "search_kb":
                    hits, provenance = _search(args.get("query_text", query), retriever)
                    for p in provenance:
                        chunks_seen[p["chunk_id"]] = p
                    result_text = _blocks(hits) if hits else "No results above the relevance threshold."
                    messages.append(
                        {"role": "tool", "tool_call_id": tc.id, "content": result_text}
                    )
                    continue

                raise RuntimeError(f"Model called unknown tool: {tc.function.name}")

        raise RuntimeError("Model did not converge on a plan within the iteration budget.")


@lru_cache
def _client() -> Optional[genai.Client]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return None
    return genai.Client(api_key=api_key)


@lru_cache
def _groq_client():
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        return None
    return Groq(api_key=api_key)


# Ordered by preference, not availability - Gemini first because it's been
# tuned against the most, Groq second as the independent-failure-domain
# fallback. Adding a third provider later is one more tuple here, not a
# rewrite: the prompt, specs, and output parsing are already provider-agnostic.
_PROVIDERS = [
    ("gemini", _client, ModelPreparer),
    ("groq", _groq_client, GroqPreparer),
]


def _is_rate_limited(exc: Exception) -> bool:
    """429 detection across both providers' distinct exception shapes.
    Gemini raises ClientError/ServerError (both APIError subclasses) with a
    real .code set from the HTTP status; Groq raises a dedicated
    RateLimitError. Deliberately narrow - only an actual quota/rate signal
    skips the same-provider retry below. Anything else (a malformed
    response, a transient 5xx) still gets retried on the same provider
    first, since switching providers on every hiccup would mask a provider-
    specific bug behind "it just fell over to Groq that time."
    """
    if isinstance(exc, GroqRateLimitError):
        return True
    return getattr(exc, "code", None) == 429


def prepare_call(query: str, student: Optional[Student], tenant: dict) -> CallPlan:
    for name, get_client, preparer_cls in _PROVIDERS:
        client = get_client()
        if client is None:
            continue
        for attempt in range(_MODEL_ATTEMPTS):
            try:
                return preparer_cls(client).prepare(query, student, tenant)
            except Exception as exc:
                if _is_rate_limited(exc):
                    # Observed directly: a 55s retry-after on an exhausted
                    # quota, twice, before giving up - a minute spent
                    # retrying a limit that hasn't reset. Go straight to the
                    # next provider instead of waiting it out here.
                    logger.warning(
                        "prepare: %s preparer rate-limited, failing over immediately (%s)",
                        name, exc,
                    )
                    break
                logger.warning(
                    "prepare: %s preparer attempt %d/%d failed (%s)",
                    name,
                    attempt + 1,
                    _MODEL_ATTEMPTS,
                    exc,
                )
                if attempt < _MODEL_ATTEMPTS - 1:
                    time.sleep(_MODEL_BACKOFF_SECONDS)
        logger.warning("prepare: %s preparer exhausted retries, trying next provider", name)

    logger.warning("prepare: all model preparers exhausted, falling back to deterministic")
    return DeterministicPreparer().prepare(query, student, tenant)
