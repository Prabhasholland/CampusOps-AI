"""CALL-E Recipient Result Schemas for CampusOps AI Operations."""

_CHANNEL = {
    "type": "string",
    "enum": ["phone", "email", "in_person", "route"],
    "description": "How this operational inquiry is resolved or concluded.",
}

# 1. Scholarship & Financial Aid Verification Schema
SCHOLARSHIP_VERIFICATION_SCHEMA = {
    "type": "object",
    "required": [
        "application_status",
        "payment_status",
        "resolved",
        "channel",
    ],
    "properties": {
        "identity_confirmed": {
            "type": "boolean",
            "description": "True if the officer/caller identity or authority was verified.",
        },
        "application_status": {
            "type": "string",
            "enum": ["approved", "under_review", "pending_documents", "rejected", "not_found"],
            "description": "Current status of the student's scholarship or bursary application.",
        },
        "payment_status": {
            "type": "string",
            "enum": ["paid", "pending", "scheduled", "blocked", "not_applicable"],
            "description": "Current state of scholarship fund disbursement.",
        },
        "expected_date": {
            "type": "string",
            "description": "Expected release date for funds or next review milestone (e.g. '2026-09-18' or 'end of month').",
        },
        "blocker_reason": {
            "type": "string",
            "description": "Explanation if payment is blocked or documents are missing.",
        },
        "additional_action_required": {
            "type": "boolean",
            "description": "True if the student or staff must submit additional forms or paperwork.",
        },
        "student_action_description": {
            "type": "string",
            "description": "Specific action required from student if additional_action_required is true.",
        },
        "confidence": {
            "type": "number",
            "description": "Estimated confidence in verified facts between 0.0 and 1.0.",
        },
        "resolved": {
            "type": "boolean",
            "description": "True if the verification produced unambiguous actionable facts.",
        },
        "channel": _CHANNEL,
        "channel_reason": {"type": "string"},
    },
}

# 2. Multi-Party Scheduling & Coordination Schema
COORDINATION_SLOT_SCHEMA = {
    "type": "object",
    "required": ["is_available", "confirmed_slot", "resolved", "channel"],
    "properties": {
        "identity_confirmed": {"type": "boolean"},
        "is_available": {
            "type": "boolean",
            "description": "Whether the participant can attend any of the proposed times.",
        },
        "preferred_slot": {
            "type": "string",
            "description": "The participant's first-choice slot (e.g. 'Tuesday 10:00 AM' or '2026-09-16 14:00').",
        },
        "confirmed_slot": {
            "type": "string",
            "description": "The specific slot agreed to during the call.",
        },
        "alternative_slots": {
            "type": "string",
            "description": "Alternative times offered if proposed slots conflicted.",
        },
        "location_preference": {
            "type": "string",
            "enum": ["in_person", "virtual_teams", "phone", "unspecified"],
            "description": "Meeting medium or venue preference.",
        },
        "meeting_notes": {
            "type": "string",
            "description": "Any specific topics, agenda items, or room requirements requested.",
        },
        "resolved": {
            "type": "boolean",
            "description": "True if slot negotiation reached a clear agreement or explicit rejection.",
        },
        "channel": _CHANNEL,
        "channel_reason": {"type": "string"},
    },
}

# 3. Proof of Registration Schema
PROOF_OF_REG_SCHEMA = {
    "type": "object",
    "required": ["resolved", "identity_confirmed", "channel"],
    "properties": {
        "identity_confirmed": {"type": "boolean"},
        "resolved": {
            "type": "boolean",
            "description": "True only if caller confirmed their question was fully answered.",
        },
        "blocker": {
            "type": "string",
            "enum": ["none", "fee_balance", "incomplete_registration", "unknown"],
        },
        "student_next_action": {"type": "string"},
        "wants_escalation": {"type": "boolean"},
        "channel": _CHANNEL,
        "channel_reason": {"type": "string"},
    },
}

# 4. Subject Cancellation Schema
SUBJECT_CANCELLATION_SCHEMA = {
    "type": "object",
    "required": ["resolved", "identity_confirmed", "channel"],
    "properties": {
        "identity_confirmed": {"type": "boolean"},
        "resolved": {"type": "boolean"},
        "subject_code": {"type": "string"},
        "within_deadline": {"type": "boolean"},
        "student_confirmed_drop": {"type": "boolean"},
        "fee_implication_explained": {"type": "boolean"},
        "wants_escalation": {"type": "boolean"},
        "channel": _CHANNEL,
        "channel_reason": {"type": "string"},
    },
}

# 5. General Institutional Triage Schema
TRIAGE_SCHEMA = {
    "type": "object",
    "required": ["category", "query_summary", "resolved", "channel"],
    "properties": {
        "identity_confirmed": {"type": "boolean"},
        "resolved": {"type": "boolean"},
        "category": {
            "type": "string",
            "enum": [
                "scholarship",
                "fees",
                "academic_records",
                "faculty_advising",
                "accommodation",
                "exams",
                "it_support",
                "unclear",
            ],
        },
        "query_summary": {"type": "string"},
        "urgency": {"type": "string", "enum": ["routine", "deadline_driven", "urgent"]},
        "action_required": {"type": "string"},
        "channel": _CHANNEL,
        "channel_reason": {"type": "string"},
    },
}


def get_schema_for_workflow(workflow_type: str, intent: str = "other") -> dict:
    if workflow_type == "verification" or intent == "scholarship_verification":
        return SCHOLARSHIP_VERIFICATION_SCHEMA
    elif workflow_type == "coordination" or intent == "multi_party_coordination":
        return COORDINATION_SLOT_SCHEMA
    elif intent == "proof_of_registration":
        return PROOF_OF_REG_SCHEMA
    elif intent == "subject_cancellation":
        return SUBJECT_CANCELLATION_SCHEMA
    return TRIAGE_SCHEMA
