from .models import Case, get_structured_result

ROUTING_TABLE = {
    ("proof_of_registration", "fee_balance"): "fees",
    ("proof_of_registration", "incomplete_registration"): "registrar",
    ("proof_of_registration", "unknown"): "registrar",
    ("other", "fees"): "fees",
    ("other", "academic_records"): "registrar",
    ("other", "faculty"): "registrar",
    ("other", "accommodation"): "accommodation",
    ("other", "exams"): "registrar",
    ("other", "it_support"): "it_support",
    ("other", "unclear"): "registrar",
}


def _office_key(case: Case, result: dict) -> str:
    if case.intent == "proof_of_registration":
        return ROUTING_TABLE.get((case.intent, result.get("blocker")), "registrar")
    if case.intent == "subject_cancellation":
        return "registrar"
    return ROUTING_TABLE.get((case.intent, result.get("category")), "registrar")


def route_case(case: Case, tenant: dict) -> None:
    result = get_structured_result(case) or {}
    office_key = _office_key(case, result)
    offices = tenant["offices"]
    office = offices.get(office_key, offices["registrar"])

    reason = (
        result.get("channel_reason")
        or result.get("query_summary")
        or result.get("student_next_action")
        or "The agent could not resolve this on the call and it needs a person to follow up."
    )

    case.routed_office = office["name"]
    case.routed_contact = f"{office['contact']} · {office['email']}"
    case.routed_reason = reason
