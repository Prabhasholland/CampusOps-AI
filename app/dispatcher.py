"""Compatibility shim for dispatcher.py pointing to app.workflows.engine."""

from typing import Optional, Dict, Any
from .workflows.engine import (
    handle_workflow_execution as handle_case,
    resume_workflow_execution as resume_case,
    calle as client,
)
from .directory import directory


def build_task(case: Any, student: Any, tenant: Dict[str, Any], briefing: str = "") -> str:
    """Builds a formatted task prompt string for phone agents."""
    parts = []
    institution = tenant.get("name", "University") if tenant else "University"
    parts.append(f"You are the CampusOps phone assistant for {institution}.")
    if case and getattr(case, "original_query", None):
        parts.append(f"Operational Inquiry: {case.original_query}")
    if briefing:
        parts.append(f"Operational Briefing: {briefing}")
    if student:
        parts.append(f"Student: {getattr(student, 'name', '')} (ID: {getattr(student, 'student_number', '')})")
        parts.append("Privacy Policy: Never state disability status, medical accommodations, or sensitive private records.")

    if tenant and "offices" in tenant:
        parts.append("Institutional Office Directory:")
        for off in tenant["offices"].values():
            parts.append(f"- {off.get('name')}: email={off.get('email')}, location={off.get('location')}")
    return "\n".join(parts)


__all__ = ["handle_case", "resume_case", "client", "directory", "build_task"]

