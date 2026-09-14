# CampusOps AI: System Architecture & Design Blueprint

## High-Level System Architecture

```mermaid
flowchart TD
    UserReq["User / Staff Operational Request<br/>('Verify delayed scholarship' or 'Schedule advising meeting')"] --> Planner["AI Operational Planner<br/>(Gemini 3.5 Flash / Groq / Deterministic)<br/>• Intent Classification<br/>• Entity & Target Directory Resolution<br/>• Multi-Step Execution Plan Generation"]
    
    Planner --> Workflows{"Workflow Orchestration Engine"}
    
    Workflows -->|Workflow 1: Verify| VerFlow["Status Verification Flow"]
    Workflows -->|Workflow 2: Coordinate| CoordFlow["Multi-Party Coordination Flow"]
    Workflows -->|Workflow 3: Escalate| EscFlow["Human Escalation Flow"]
    
    VerFlow --> CalleExec["CALL-E Phone Dispatcher<br/>(Dynamic JSON Schemas + E.164 + Retries)"]
    CoordFlow --> CalleExec
    
    CalleExec --> RealCall["Live Telephony / Mock Simulation"]
    RealCall --> ExtractedResult["Structured Call Result<br/>+ Turn-by-Turn Transcripts<br/>+ Real-time Evidence"]
    
    ExtractedResult --> Verifier["Evidence Verification Engine<br/>• Required Facts Checklist<br/>• Policy Rule Validation<br/>• Confidence Score Scoring (0.0 - 1.0)"]
    
    Verifier --> Decision{"Verification Decision"}
    
    Decision -->|Verified (Score >= 0.85)| CaseResolved["CASE RESOLVED ✓<br/>(Updated in SIS & Records)"]
    Decision -->|Incomplete Facts| RetryStep["Second Targeted Call / Step Advancement"]
    Decision -->|Policy Blocker / Conflict| HumanEscalation["Human Escalation Packet<br/>• Root Cause Analysis<br/>• Key Transcript Quotes<br/>• Actionable Staff Recommendations"]
    
    RetryStep --> CalleExec
    HumanEscalation --> StaffInbox["Staff Review Queue"]
```

## Architectural Pillars

### 1. Multi-Provider Operational Planner (`app/agents/planner.py`)
- Transforms unstructured prompts into structured, typed `ExecutionPlan` models.
- Employs a resilient failover chain:
  1. **Google Gemini 3.5 Flash Lite**: Deep contextual reasoning over institutional guidelines.
  2. **Groq (OpenAI-compatible GPT-OSS 120b)**: Independent fallback failure domain.
  3. **Deterministic Planner**: Rule-based regex & directory lookups ensuring 100% offline availability.

### 2. Evidence Verification Loop (`app/agents/verifier.py`)
- Performs rigorous post-call fact checking.
- Checks whether required fields (`application_status`, `payment_status`, `expected_date`) were successfully populated.
- Computes weighted confidence metrics:
  $$\text{Evidence Score} = 0.5 \times \left(\frac{\text{Satisfied Requirements}}{\text{Total Requirements}}\right) + 0.5 \times \text{CALL-E Confidence}$$
- Gates case resolution behind strict policy verification.

### 3. Multi-Party Coordination Engine (`app/workflows/coordination_flow.py`)
- Sequentially negotiates calendar consensus across distinct stakeholders.
- Avoids concurrent dialing collisions and handles scheduling conflicts with automated fallback proposals.

### 4. Human Escalation Engine (`app/agents/escalation.py`)
- When automation cannot or should not proceed (e.g. missing parental affidavits or legal matters), synthesizes a complete review brief for human staff.
