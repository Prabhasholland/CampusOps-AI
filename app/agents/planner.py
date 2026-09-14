"""Operational AI Planner for CampusOps AI.

Understands high-level institutional requests, determines workflow types (Verification,
Multi-Party Coordination, Escalation, General), resolves contact targets from the
institutional directory, and creates structured multi-step execution plans.
"""

import datetime
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field, asdict
from functools import lru_cache
from typing import List, Optional, Protocol, Dict, Any

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None
    types = None

try:
    from groq import Groq, RateLimitError as GroqRateLimitError
except ImportError:
    Groq = None
    GroqRateLimitError = Exception

from ..directory import directory as campus_directory, StudentRecord, format_currency
from ..retrieval import get_retriever, build_briefing, _search, _blocks

logger = logging.getLogger(__name__)

GEMINI_MODEL = "gemini-3.5-flash-lite"
GROQ_MODEL = "openai/gpt-oss-120b"
MAX_ITERATIONS = 2
_MODEL_ATTEMPTS = 2
_MODEL_BACKOFF_SECONDS = 1.5


@dataclass
class PlanStep:
    step_number: int
    target_role: str  # student | faculty | department_office | scholarship_office | external_verifier
    target_name: str
    target_phone: str
    task_instructions: str
    schema_type: str  # scholarship | coordination | triage | proof_of_reg | subject_drop
    required_fields: List[str] = field(default_factory=list)


@dataclass
class ExecutionPlan:
    workflow_type: str  # verification | coordination | escalation | general
    intent: str
    priority: str  # low | medium | high | urgent
    reasoning: str
    briefing: str
    should_call: bool
    target_entities: List[Dict[str, str]] = field(default_factory=list)
    required_facts: List[str] = field(default_factory=list)
    steps: List[PlanStep] = field(default_factory=list)
    route_to: Optional[str] = None
    sources_used: List[dict] = field(default_factory=list)
    confidence: str = "medium"
    preparer_used: str = "deterministic"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class PlannerStrategy(Protocol):
    def plan(self, query: str, student: Optional[StudentRecord], tenant: dict) -> ExecutionPlan: ...


class DeterministicPlanner:
    """Deterministic fallback planner using institutional pattern recognition & directory lookup."""

    def plan(self, query: str, student: Optional[StudentRecord], tenant: dict) -> ExecutionPlan:
        q = query.lower()
        now_date = datetime.date.today().isoformat()

        # 1. Detection of Multi-Party Coordination
        if any(w in q for w in ["schedule", "meeting", "meet with", "coordinate", "appointment", "advisor", "advising", "faculty"]):
            # Identify faculty & department
            faculty = campus_directory.lookup_faculty("alweendo") or campus_directory.list_faculty()[0]
            dept = campus_directory.lookup_office("fci_department") or campus_directory.list_offices()[0]
            student_name = student.name if student else "Student"
            student_phone = student.phone if student else "+264812345678"

            steps = [
                PlanStep(
                    step_number=1,
                    target_role="student",
                    target_name=student_name,
                    target_phone=student_phone,
                    task_instructions=(
                        f"Call student {student_name} to negotiate preferred meeting times with academic advisor "
                        f"{faculty.name}. Ask for 2-3 candidate slots this week and note specific topics to cover."
                    ),
                    schema_type="coordination",
                    required_fields=["is_available", "preferred_slot", "confirmed_slot"],
                ),
                PlanStep(
                    step_number=2,
                    target_role="faculty",
                    target_name=faculty.name,
                    target_phone=faculty.phone,
                    task_instructions=(
                        f"Call advisor {faculty.name} ({faculty.department}) to verify availability for the slot "
                        f"proposed by {student_name}. Confirm venue ({faculty.office_location}) and advising notes."
                    ),
                    schema_type="coordination",
                    required_fields=["is_available", "confirmed_slot"],
                ),
                PlanStep(
                    step_number=3,
                    target_role="department_office",
                    target_name=dept.name,
                    target_phone=dept.phone,
                    task_instructions=(
                        f"Call {dept.name} ({dept.officer_name}) to register the confirmed meeting in the department "
                        f"calendar and ensure room access."
                    ),
                    schema_type="coordination",
                    required_fields=["confirmed_slot", "resolved"],
                ),
            ]

            return ExecutionPlan(
                workflow_type="coordination",
                intent="multi_party_coordination",
                priority="high",
                reasoning="Identified request to schedule an advising session requiring 3-way coordination (Student, Advisor, Department).",
                briefing=f"Coordinate academic advising meeting between {student_name} and {faculty.name}.",
                should_call=True,
                target_entities=[
                    {"role": "student", "name": student_name, "phone": student_phone},
                    {"role": "faculty", "name": faculty.name, "phone": faculty.phone},
                    {"role": "department_office", "name": dept.name, "phone": dept.phone},
                ],
                required_facts=["confirmed_slot", "is_available", "resolved"],
                steps=steps,
                confidence="high",
                preparer_used="deterministic",
            )

        # 2. Detection of Scholarship / Financial Aid Verification
        if any(w in q for w in ["scholarship", "bursary", "financial aid", "nsfas", "delayed", "payment status", "funds", "disbursement"]):
            student_ref = student.student_number if student else "220012345"
            if student_ref == "220034567" or "josef" in q:
                target_office = campus_directory.lookup_office("fees")
                target_phone = "+264813456789"
                target_name = "Financial Aid & Fees Counter"
            else:
                scholarship_office = campus_directory.lookup_office("scholarship")
                target_phone = scholarship_office.phone if scholarship_office else "+264811234567"
                target_name = scholarship_office.name if scholarship_office else "Scholarship Bureau"

            steps = [
                PlanStep(
                    step_number=1,
                    target_role="scholarship_office",
                    target_name=target_name,
                    target_phone=target_phone,
                    task_instructions=(
                        f"Call {target_name} regarding scholarship verification for student ID {student_ref}. "
                        "Determine: 1) Application status (approved/pending/rejected), 2) Payment status, "
                        "3) Expected disbursement date, and 4) If any additional student action is required."
                    ),
                    schema_type="scholarship",
                    required_fields=["application_status", "payment_status", "expected_date"],
                )
            ]

            return ExecutionPlan(
                workflow_type="verification",
                intent="scholarship_verification",
                priority="high",
                reasoning="Identified scholarship inquiry requiring phone verification of payment status and disbursement timeline.",
                briefing=f"Verify scholarship status and disbursement date for student {student_ref} with {target_name}.",
                should_call=True,
                target_entities=[
                    {"role": "scholarship_office", "name": target_name, "phone": target_phone}
                ],
                required_facts=["application_status", "payment_status", "expected_date"],
                steps=steps,
                confidence="high",
                preparer_used="deterministic",
            )

        # 3. Detection of Sensitive / Direct Human Escalation
        if any(w in q for w in ["legal", "police", "harassment", "disciplinary", "appeal", "visa", "permit", "distress"]):
            registrar = campus_directory.lookup_office("registrar")
            return ExecutionPlan(
                workflow_type="escalation",
                intent="sensitive_escalation",
                priority="urgent",
                reasoning="Inquiry contains sensitive, legal, immigration, or disciplinary terms requiring direct human handling.",
                briefing="Sensitive matter flagged by safety guardrails. Routed directly to administration without automated phone call.",
                should_call=False,
                route_to="registrar",
                confidence="high",
                preparer_used="deterministic",
            )

        # 4. Standard Student Inquiry (Proof of Reg / Subject / General)
        retriever = get_retriever(tenant.get("id", "nust"))
        briefing, sources, _ = build_briefing(query, retriever, tenant)

        intent = "general_inquiry"
        schema_type = "triage"
        if "registration" in q or "proof" in q:
            intent = "proof_of_registration"
            schema_type = "proof_of_reg"
        elif "cancel" in q or "drop" in q:
            intent = "subject_cancellation"
            schema_type = "subject_drop"

        caller_phone = student.phone if student else "+264811234567"
        caller_name = student.name if student else "Caller"

        steps = [
            PlanStep(
                step_number=1,
                target_role="student",
                target_name=caller_name,
                target_phone=caller_phone,
                task_instructions=briefing,
                schema_type=schema_type,
                required_fields=["resolved", "identity_confirmed"],
            )
        ]

        return ExecutionPlan(
            workflow_type="general",
            intent=intent,
            priority="medium",
            reasoning="Standard academic inquiry resolved via grounded institutional knowledge base.",
            briefing=briefing,
            should_call=True,
            target_entities=[{"role": "student", "name": caller_name, "phone": caller_phone}],
            required_facts=["resolved"],
            steps=steps,
            sources_used=sources,
            confidence="medium",
            preparer_used="deterministic",
        )


class GeminiPlanner:
    """Gemini-powered Operational Planner."""

    def __init__(self, client: genai.Client, model: str = GEMINI_MODEL):
        self._client = client
        self._model = model

    def plan(self, query: str, student: Optional[StudentRecord], tenant: dict) -> ExecutionPlan:
        # Prompt engineered for structured multi-step institutional planning
        prompt = f"""You are the Operational AI Planner for {tenant.get('short_name', 'NUST')}'s autonomous phone operations system (CampusOps AI).
An operational request has been submitted: "{query}"

Student Context (if available):
{json.dumps(student.model_dump(mode='json') if student else 'No student record found', indent=2, default=str)}

Your task is to analyze the operational request and return a structured JSON plan with:
- workflow_type: one of ["verification", "coordination", "escalation", "general"]
- intent: descriptive intent identifier
- priority: "low" | "medium" | "high" | "urgent"
- reasoning: why this workflow and steps are chosen
- should_call: true (unless sensitive/legal/visa matter needing direct human routing)
- required_facts: list of fact field names that must be verified (e.g. ["application_status", "payment_status", "expected_date"])
- steps: array of execution steps (step_number, target_role, target_name, target_phone, task_instructions, schema_type, required_fields)

Return ONLY valid JSON matching this structure.
"""
        response = self._client.models.generate_content(
            model=self._model,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0.1,
            ),
        )

        raw_text = response.text or "{}"
        data = json.loads(raw_text)

        steps = [
            PlanStep(
                step_number=s.get("step_number", i + 1),
                target_role=s.get("target_role", "target"),
                target_name=s.get("target_name", "Staff"),
                target_phone=s.get("target_phone", student.phone if student else "+264811234567"),
                task_instructions=s.get("task_instructions", query),
                schema_type=s.get("schema_type", "scholarship"),
                required_fields=s.get("required_fields", []),
            )
            for i, s in enumerate(data.get("steps", []))
        ]

        if not steps:
            # Fallback to single step if model omitted steps
            steps = [
                PlanStep(
                    step_number=1,
                    target_role="student",
                    target_name=student.name if student else "Caller",
                    target_phone=student.phone if student else "+264811234567",
                    task_instructions=query,
                    schema_type="triage",
                    required_fields=["resolved"],
                )
            ]

        return ExecutionPlan(
            workflow_type=data.get("workflow_type", "verification"),
            intent=data.get("intent", "operational_task"),
            priority=data.get("priority", "medium"),
            reasoning=data.get("reasoning", "Plan synthesized by Gemini model."),
            briefing=data.get("briefing", query),
            should_call=data.get("should_call", True),
            target_entities=data.get("target_entities", []),
            required_facts=data.get("required_facts", []),
            steps=steps,
            route_to=data.get("route_to"),
            confidence="high",
            preparer_used="gemini",
        )


@lru_cache
def _get_gemini_client() -> Optional[Any]:
    if genai is None:
        return None
    key = os.environ.get("GEMINI_API_KEY")
    return genai.Client(api_key=key) if key and key.strip() else None


class OperationalPlanner:
    """Main Operational Planner interface with resilient provider failover."""

    def __init__(self):
        self._deterministic = DeterministicPlanner()

    def plan(self, query: str, student: Optional[StudentRecord], tenant: dict) -> ExecutionPlan:
        gemini_client = _get_gemini_client()
        if gemini_client:
            try:
                logger.info("planner: running Gemini operational planning pass")
                return GeminiPlanner(gemini_client).plan(query, student, tenant)
            except Exception as exc:
                logger.warning("planner: Gemini planning pass failed, falling back (%s)", exc)

        logger.info("planner: running Deterministic operational planner pass")
        return self._deterministic.plan(query, student, tenant)


# Singleton instance
planner = OperationalPlanner()
