"""CALL-E Client & Transport Abstraction for CampusOps AI.

Supports both live production calls via CALL-E's REST API and realistic,
deterministic mock simulations for local development, demos, and testing.
"""

import os
import time
import uuid
from typing import Optional, List, Dict, Any

from dotenv import load_dotenv
load_dotenv()

import httpx

from .results import CallResult, parse_call_response



_TRANSIENT_ATTEMPTS = 3
_TRANSIENT_BACKOFF_SECONDS = 1.5


def _is_retryable_status(exc: httpx.HTTPStatusError) -> bool:
    code = exc.response.status_code
    return code == 429 or code >= 500


def _with_retry(fn):
    last_exc: Optional[Exception] = None
    for attempt in range(_TRANSIENT_ATTEMPTS):
        try:
            return fn()
        except httpx.TransportError as exc:
            last_exc = exc
            if attempt < _TRANSIENT_ATTEMPTS - 1:
                time.sleep(_TRANSIENT_BACKOFF_SECONDS * (attempt + 1))
        except httpx.HTTPStatusError as exc:
            if not _is_retryable_status(exc):
                raise
            last_exc = exc
            if attempt < _TRANSIENT_ATTEMPTS - 1:
                time.sleep(_TRANSIENT_BACKOFF_SECONDS * (attempt + 1))
    raise last_exc


class _RealTransport:
    """Live CALL-E REST API Transport."""

    def __init__(self, api_key: str, base_url: str):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=30,
        )

    def dispatch(
        self,
        task: str,
        phone: str,
        result_schema: dict,
        region: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> str:
        recipient = {"phones": [phone]}
        if region:
            recipient["region"] = region
        if locale:
            recipient["locale"] = locale

        def _do():
            response = self._client.post(
                "/v1/calls",
                json={
                    "task": task,
                    "recipients": [recipient],
                    "recipient_result_schema": result_schema,
                },
            )
            response.raise_for_status()
            return response.json()["id"]

        return _with_retry(_do)

    def get_result(self, run_id: str) -> CallResult:
        def _do():
            response = self._client.get(f"/v1/calls/{run_id}")
            response.raise_for_status()
            return response.json()

        return parse_call_response(_with_retry(_do))


class _MockTransport:
    """Deterministic Mock Transport for local testing, CI, and dry-run demos."""

    _SCENARIOS = {
        # Scenario 1: Scholarship Office Verification (Success - Approved & Pending Date)
        "+264811234567": {
            "delay": 2.5,
            "status": "COMPLETED",
            "extracted": {
                "identity_confirmed": True,
                "application_status": "approved",
                "payment_status": "pending",
                "expected_date": "2026-09-18",
                "blocker_reason": "None. Batch payment queued for financial clearance.",
                "additional_action_required": False,
                "confidence": 0.94,
                "resolved": True,
                "channel": "phone",
                "channel_reason": "Scholarship status confirmed as approved with disbursement date on file.",
            },
            "evidence": [
                "Officer Hilma Shipanga confirmed student file SCH-92831 is approved.",
                "Disbursement batch #4 is scheduled for release on 2026-09-18.",
                "No outstanding documentation is required from the student.",
            ],
            "transcript_turns": [
                {"speaker": "bot", "text": "Hello, I am the CampusOps Autonomous Assistant calling on behalf of the university regarding scholarship verification for student 220012345. May I confirm the application status?"},
                {"speaker": "user", "text": "Yes, let me pull up the record... Okay, application SCH-92831 is approved."},
                {"speaker": "bot", "text": "Thank you. Has payment been disbursed, or is there an expected payment date?"},
                {"speaker": "user", "text": "It is currently pending clearance, scheduled for release on September 18th, 2026."},
                {"speaker": "bot", "text": "Is any further action required from the student?"},
                {"speaker": "user", "text": "No, everything is in order."},
                {"speaker": "bot", "text": "Thank you for your assistance. Have a great day!"}
            ],
        },

        # Scenario 2: Multi-Party Coordination Step 1 (Student Availability Negotiation)
        "+264812345678": {
            "delay": 2.0,
            "status": "COMPLETED",
            "extracted": {
                "identity_confirmed": True,
                "is_available": True,
                "preferred_slot": "Tuesday 2:00 PM",
                "confirmed_slot": "Tuesday 2:00 PM",
                "alternative_slots": "Tuesday 10:00 AM, Wednesday 10:00 AM",
                "location_preference": "in_person",
                "meeting_notes": "Discussing subject prerequisite waiver and graduation track.",
                "resolved": True,
                "channel": "phone",
            },
            "evidence": [
                "Student Maria Nghipandulwa confirmed availability for Tuesday at 2:00 PM.",
                "Secondary backup slot offered: Tuesday 10:00 AM.",
            ],
            "transcript_turns": [
                {"speaker": "bot", "text": "Hello Maria, this is CampusOps calling from NUST to coordinate your academic advising session. When are you available this week?"},
                {"speaker": "user", "text": "Hi! Tuesday afternoon around 2:00 PM would be ideal for me, or Tuesday morning at 10:00 AM."},
                {"speaker": "bot", "text": "Got it. Tuesday 2:00 PM as preferred, with 10:00 AM as backup. We will coordinate with Dr. Alweendo and confirm."},
            ],
        },

        # Scenario 3: Multi-Party Coordination Step 2 (Faculty Advisor Confirmation)
        "+264815678901": {
            "delay": 2.0,
            "status": "COMPLETED",
            "extracted": {
                "identity_confirmed": True,
                "is_available": True,
                "preferred_slot": "Tuesday 2:00 PM",
                "confirmed_slot": "Tuesday 2:00 PM",
                "alternative_slots": "Thursday 2:00 PM",
                "location_preference": "in_person",
                "meeting_notes": "Advising room 302 available.",
                "resolved": True,
                "channel": "phone",
            },
            "evidence": [
                "Dr. Johannes Alweendo confirmed availability for Tuesday 2:00 PM in FCI Room 302.",
            ],
            "transcript_turns": [
                {"speaker": "bot", "text": "Hello Dr. Alweendo, this is CampusOps calling to coordinate an advising meeting with Maria Nghipandulwa. Is Tuesday at 2:00 PM open in your calendar?"},
                {"speaker": "user", "text": "Yes, Tuesday 2:00 PM works perfectly. We can meet in my office, FCI 302."},
                {"speaker": "bot", "text": "Wonderful. We will finalize the booking with the department office. Thank you!"},
            ],
        },

        # Scenario 4: Multi-Party Coordination Step 3 (Department Admin Booking)
        "+264816789012": {
            "delay": 2.0,
            "status": "COMPLETED",
            "extracted": {
                "identity_confirmed": True,
                "is_available": True,
                "confirmed_slot": "Tuesday 2:00 PM",
                "location_preference": "in_person",
                "meeting_notes": "Room FCI 302 calendar reserved and entry pass approved.",
                "resolved": True,
                "channel": "phone",
            },
            "evidence": [
                "FCI Department Admin confirmed calendar reservation for Tuesday 2:00 PM.",
                "Room FCI 302 reserved and notification dispatched to all parties.",
            ],
            "transcript_turns": [
                {"speaker": "bot", "text": "Hello Ms. Shilongo, CampusOps calling to reserve FCI Room 302 for an advising session on Tuesday at 2:00 PM between Maria Nghipandulwa and Dr. Alweendo."},
                {"speaker": "user", "text": "Room 302 is available and I have entered the booking on the calendar."},
                {"speaker": "bot", "text": "Thank you so much! All participants will receive confirmation."},
            ],
        },

        # Scenario 5: Missing / Incomplete Evidence (Triggers Escalation or Second Call)
        "+264813456789": {
            "delay": 2.0,
            "status": "COMPLETED",
            "extracted": {
                "identity_confirmed": True,
                "application_status": "pending_documents",
                "payment_status": "blocked",
                "expected_date": None,
                "blocker_reason": "Missing parent tax affidavit for income verification.",
                "additional_action_required": True,
                "student_action_description": "Submit certified 2025 income affidavit to Financial Aid Counter 4.",
                "confidence": 0.62,
                "resolved": False,
                "channel": "route",
                "channel_reason": "Application blocked by policy requirement; human staff follow-up needed.",
            },
            "evidence": [
                "Application is held in pending_documents status.",
                "Payment is blocked until original certified affidavit is inspected.",
            ],
            "transcript_turns": [
                {"speaker": "bot", "text": "CampusOps calling regarding scholarship status for student Josef Kambala. Can you provide the current payment status?"},
                {"speaker": "user", "text": "The payment is currently blocked because the student's 2025 parental income affidavit was missing."},
                {"speaker": "bot", "text": "Is there an expected date for disbursement once submitted?"},
                {"speaker": "user", "text": "No date can be given until the physical certified copy is presented at Counter 4."},
            ],
        },

        # Scenario 6: No Answer / Unreachable
        "+264814567890": {
            "delay": 1.5,
            "status": "NO ANSWER",
            "extracted": None,
            "evidence": [],
            "transcript_turns": [],
        },
    }

    def __init__(self):
        self._runs: Dict[str, Any] = {}

    def dispatch(
        self,
        task: str,
        phone: str,
        result_schema: dict,
        region: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> str:
        run_id = f"mock_{uuid.uuid4().hex[:10]}"
        # If specific phone scenario not matched, provide a safe synthetic completed scenario
        scenario = self._SCENARIOS.get(phone)
        if not scenario:
            scenario = {
                "delay": 2.0,
                "status": "COMPLETED",
                "extracted": {
                    "identity_confirmed": True,
                    "resolved": True,
                    "channel": "phone",
                    "confidence": 0.90,
                    "query_summary": "Inquiry successfully resolved via operational phone assistant.",
                },
                "evidence": ["Recipient confirmed details during call."],
                "transcript_turns": [
                    {"speaker": "bot", "text": "Hello, this is the CampusOps Assistant regarding your institutional query."},
                    {"speaker": "user", "text": "Yes, thank you for following up."},
                    {"speaker": "bot", "text": "We have processed the necessary steps according to policy."},
                    {"speaker": "user", "text": "That completely resolves my question, thank you."},
                ],
            }

        self._runs[run_id] = {
            "started": time.monotonic(),
            "scenario": scenario,
            "schema": result_schema,
            "phone": phone,
        }
        return run_id

    def get_result(self, run_id: str) -> CallResult:
        run = self._runs.get(run_id)
        if run is None:
            return parse_call_response({"status": "FAILED"})

        elapsed = time.monotonic() - run["started"]
        if elapsed < run["scenario"]["delay"]:
            return parse_call_response(
                {"status": "PREPARING", "next_step": {"poll_after_seconds": 1.5}}
            )

        scenario = run["scenario"]
        if scenario["status"] != "COMPLETED":
            return parse_call_response({"status": scenario["status"]})

        extracted = dict(scenario["extracted"] or {})
        return parse_call_response(
            {
                "status": "COMPLETED",
                "task_completed": True,
                "completion_confidence": {"score": extracted.get("confidence", 0.90), "label": "high"},
                "evidence": scenario.get("evidence", ["Verified against institutional mock data."]),
                "summary": "CampusOps operational phone task completed.",
                "post_summary": "Task concluded.",
                "recipients": [
                    {
                        "structured_result": extracted,
                        "attempts": [{"transcript_turns": scenario.get("transcript_turns", [])}],
                    }
                ],
            }
        )


class CalleClient:
    """Primary client interface for CALL-E operations in CampusOps AI."""

    def __init__(self, force_mock: bool = False):
        force_mock = force_mock or os.environ.get("CALLE_MOCK", "").lower() in ("1", "true", "yes")
        api_key = os.environ.get("CALLE_API_KEY")
        base_url = os.environ.get("CALLE_BASE_URL", "https://api.heycall-e.com")
        if not force_mock and api_key and api_key.strip():
            self._transport = _RealTransport(api_key.strip(), base_url)
            self.is_live = True
        else:
            self._transport = _MockTransport()
            self.is_live = False

    def dispatch(
        self,
        task: str,
        phone: str,
        result_schema: dict,
        region: Optional[str] = None,
        locale: Optional[str] = None,
    ) -> str:
        return self._transport.dispatch(task, phone, result_schema, region=region, locale=locale)

    def get_result(self, run_id: str) -> CallResult:
        return self._transport.get_result(run_id)


# Backward compatibility alias
calle_client_instance = CalleClient()
