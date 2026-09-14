---
name: campus-phone-operations
description: Autonomous phone operations for institutions, orchestrating verification loops, multi-party advising coordination, and human escalation via CALL-E.
---

# Campus Phone Operations

Automates complex phone operations for higher education and institutional administrative offices using CALL-E.

This skill equips an AI assistant with the ability to plan operational workflows, dial institutional contacts, extract structured evidence, coordinate schedules among multiple stakeholders, verify extracted facts against policy checklists, and safely escalate unresolved matters to human staff.

## Core Workflows

1. **Autonomous Verification Loop (`verification`)**:
   - Gathers student context and institutional policy.
   - Places a phone call to the scholarship or administrative bureau.
   - Extracts structured facts: application status, payment disbursement state, and expected completion date.
   - Evaluates evidence confidence. If complete, resolves case; if blocked, builds staff action packet.

2. **Multi-Party Coordination (`coordination`)**:
   - Sequences phone calls across multiple stakeholders (Student -> Faculty Advisor -> Department Office).
   - Negotiates candidate time slots iteratively to reach consensus.
   - Confirms calendar reservations and room bookings.

3. **Direct Escalation & Safety Guardrails (`escalation`)**:
   - Intercepts sensitive, legal, or immigration matters without placing unverified calls.
   - Formulates structured escalation briefs with root-cause analysis and recommended staff actions.

## References

- Follow the workflow safety rules in [references/safety.md](references/safety.md).
- See detailed prompt-to-call execution transcripts in [references/examples.md](references/examples.md).

## Usage Pattern

```python
from app.agents.planner import planner
from app.workflows.engine import handle_workflow_execution

# 1. Plan operational request
plan = planner.plan(
    query="A student's scholarship is delayed. Find out the status and resolve it.",
    student=student_record,
    tenant=tenant_config,
)

# 2. Execute autonomous workflow with verification loop
await handle_workflow_execution(case_id=101)
```
