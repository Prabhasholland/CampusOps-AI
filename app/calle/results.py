"""CALL-E Response Parser & Result Dataclass.

Defensively parses raw get_call_run payloads captured from real CALL-E runs.
"""

from dataclasses import dataclass
from typing import List, Optional, Any, Dict


@dataclass
class CallResult:
    status: str  # in_progress | completed | no_answer | declined | failed | <other>
    structured_result: Optional[dict] = None
    transcript: Optional[str] = None
    completion_confidence: Optional[float] = None
    task_completed: Optional[bool] = None
    evidence: Optional[List[str]] = None
    summary: Optional[str] = None
    post_summary: Optional[str] = None
    poll_after_seconds: Optional[float] = None

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "structured_result": self.structured_result,
            "transcript": self.transcript,
            "completion_confidence": self.completion_confidence,
            "task_completed": self.task_completed,
            "evidence": self.evidence,
            "summary": self.summary,
            "post_summary": self.post_summary,
            "poll_after_seconds": self.poll_after_seconds,
        }



_IN_PROGRESS_STATUSES = {"QUEUED", "PREPARING", "SCHEDULED"}
_TERMINAL_STATUS_MAP = {
    "COMPLETED": "completed",
    "NO ANSWER": "no_answer",
    "DECLINED": "declined",
    "FAILED": "failed",
}


def _poll_after_seconds(data: dict) -> Optional[float]:
    next_step = data.get("next_step") or {}
    value = next_step.get("poll_after_seconds")
    if isinstance(value, (int, float)):
        return max(1.0, float(value))
    return None


def _format_transcript(turns) -> Optional[str]:
    if not turns:
        return None
    lines = [f"{t.get('speaker', '?')}: {t.get('text', '')}" for t in turns if isinstance(t, dict)]
    return "\n".join(lines) if lines else None


def parse_call_response(data: dict) -> CallResult:
    """Maps a raw call-status payload from CALL-E to a CallResult."""
    raw_status = str(data.get("status") or "").strip().upper()
    poll_after = _poll_after_seconds(data)

    if not raw_status or raw_status in _IN_PROGRESS_STATUSES:
        return CallResult(status="in_progress", poll_after_seconds=poll_after)

    status = _TERMINAL_STATUS_MAP.get(raw_status, raw_status.lower().replace(" ", "_"))

    recipients = data.get("recipients") or []
    recipient = recipients[0] if recipients else {}
    structured = recipient.get("structured_result")
    if not isinstance(structured, dict):
        structured = data.get("structured_result")

    attempts = recipient.get("attempts") or []
    transcript = _format_transcript(attempts[-1].get("transcript_turns")) if attempts else None

    confidence = data.get("completion_confidence")
    confidence_score = confidence.get("score") if isinstance(confidence, dict) else confidence

    return CallResult(
        status=status,
        structured_result=structured,
        transcript=transcript,
        completion_confidence=confidence_score,
        task_completed=data.get("task_completed"),
        evidence=data.get("evidence"),
        summary=data.get("summary"),
        post_summary=data.get("post_summary"),
        poll_after_seconds=poll_after,
    )
