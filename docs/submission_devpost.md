# CampusOps AI: Autonomous Phone Operations for Institutions
## Devpost Hackathon Submission Deliverable & Pitch Packet

---

### Quick Project Summary
- **Project Name**: CampusOps AI
- **Tagline**: Autonomous multi-step phone operations for institutions powered by CALL-E — Automated verification, 3-way multi-party coordination, and human-in-the-loop escalation.
- **Repository Track**: CALL-E Hackathon / Awesome Phone Call Agents
- **Primary Agent Skill**: `skills/campus-phone-operations/`
- **Demo Dashboard**: React 18 + Vite + Tailwind CSS Operations Command Center
- **Backend**: Python 3.14 + FastAPI + SQLModel + CALL-E API + Google Gemini

---

## 1. Inspiration & The Problem

Universities and educational institutions handle hundreds of thousands of complex operational inquiries every academic semester:
- **Scholarship & Financial Aid Bottlenecks**: Students waiting weeks for bursary disbursements must repeatedly visit administrative counters or make dozens of phone calls just to check if a single form was stamped.
- **Multi-Party Coordination Friction**: Booking an academic advising meeting requires back-and-forth communication between the student, a faculty advisor, and the department office to confirm times, prerequisites, and room availability.
- **Single-Turn Callback Limitations**: Traditional AI phone bots simply read back static FAQs. When an inquiry encounters an institutional policy blocker (e.g. missing parent tax affidavit), traditional bots either get stuck in loops or drop the call.

**CampusOps AI** turns the phone into an **autonomous operational instrument**. Instead of passive callbacks, CampusOps AI plans multi-step operational campaigns, dials the necessary offices or parties using CALL-E, verifies extracted evidence against institutional criteria, and autonomously resolves cases or escalates them with actionable human briefs.

---

## 2. What CampusOps AI Does

CampusOps AI provides three flagship operational workflows:

```
                      ┌─────────────────────────────────────────┐
                      │        Institutional Inquiry            │
                      │  (Student Portal / Voice / Helpdesk)    │
                      └────────────────────┬────────────────────┘
                                           │
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │       AI Operational Planner            │
                      │  (Intent Routing & Step Decomposition)  │
                      └────────────────────┬────────────────────┘
                                           │
         ┌─────────────────────────────────┼─────────────────────────────────┐
         ▼                                 ▼                                 ▼
┌──────────────────┐             ┌──────────────────┐             ┌──────────────────┐
│   WORKFLOW 1     │             │   WORKFLOW 2     │             │   WORKFLOW 3     │
│   Verification   │             │   Coordination   │             │   Escalation     │
│                  │             │                  │             │                  │
│ • Dial Aid Office│             │ • Step 1: Student│             │ • Policy Blocker │
│ • Extract Status │             │ • Step 2: Faculty│             │ • Low Confidence │
│ • Check Milestones│            │ • Step 3: Admin  │             │ • Staff Briefing │
└────────┬─────────┘             └────────┬─────────┘             └────────┬─────────┘
         │                                │                                │
         └────────────────────────────────┼────────────────────────────────┘
                                           ▼
                      ┌─────────────────────────────────────────┐
                      │    Post-Call Evidence Verification      │
                      │  (Completeness & Confidence Assessment) │
                      └────────────────────┬────────────────────┘
                                           │
                         ┌─────────────────┴─────────────────┐
                         ▼                                   ▼
              [ Verified: >= 85% ]                 [ Missing / Blocked ]
              Auto-Resolve & Notify               Escalate Action Brief
```

### 1. Scholarship & Bursary Verification Flow
- **Goal**: Resolve delayed financial aid inquiries by actively calling the Financial Aid Office.
- **Mechanism**: The agent uses CALL-E to reach the scholarship officer, provides the student reference, and extracts 4 required facts: application approval status, disbursement state, expected disbursement date, and required student actions.
- **Outcome**: The post-call Evidence Verifier evaluates the returned facts. If confidence is $\ge 85\%$ and facts are verified, the case is automatically resolved and logged.

### 2. 3-Way Multi-Party Advising Coordination Flow
- **Goal**: Seamlessly book an advising session across multiple independent stakeholders without human email tag.
- **Step 1 (Student)**: Calls student to negotiate preferred and backup timeslots (e.g. Tuesday 2:00 PM).
- **Step 2 (Faculty)**: Dials faculty advisor (Dr. Alweendo) to confirm availability and office venue.
- **Step 3 (Department)**: Dials department admin to book room calendar and dispatch access pass.
- **Outcome**: Multi-party matrix confirmed and calendar invitations generated.

### 3. Policy Blocker & Human-in-the-Loop Escalation Flow
- **Goal**: Handle exceptions safely without leaving students in bureaucratic limbo.
- **Mechanism**: If a call uncovers a policy hold (e.g., *Missing parent tax affidavit for income verification*) or confidence falls below threshold, the Escalation Engine generates a structured Staff Action Packet:
  - Immediate recommended staff action with office routing (Counter 4).
  - Exact blocker rationale.
  - Verbatim audio transcript turns with speaker tags.
  - One-click staff resolution buttons in the Command Center.

---

## 3. Technical Architecture & Innovation

### 1. Robust CALL-E Transport & Schema Enforcement
- **Dual Transport Mode**: Live REST API client with exponential backoff on 429/5xx errors + deterministic mock transport for instant offline testing and CI/CD.
- **Strict JSON Schemas**: Every CALL-E call is bound to a schema (`SCHOLARSHIP_VERIFICATION_SCHEMA`, `COORDINATION_SLOT_SCHEMA`, etc.) guaranteeing structured, type-safe post-call payload extraction.

### 2. Evidence Verification Engine (`app/agents/verifier.py`)
- Standard phone bots assume that if a call ends, the task is finished.
- CampusOps AI enforces an **Evidence Verification Loop**:
  - Checks presence and validity of critical institutional facts.
  - Computes a mathematical composite evidence score:
    $$\text{Score} = 0.5 \times \left(\frac{\text{Facts Satisfied}}{\text{Total Required}}\right) + 0.5 \times (\text{Confidence})$$
  - Enforces $\ge 85\%$ threshold before marking any case as resolved.

### 3. Multi-Tier Planning Failover
- **Tier 1**: Google Gemini 3.5 Flash Lite with structured reasoning over institutional directories.
- **Tier 2**: Groq `openai/gpt-oss-120b` fallback for distinct failure domains.
- **Tier 3**: Deterministic regex & keyword planner for zero-downtime offline execution.

### 4. Portable Agent Skill (`skills/campus-phone-operations/`)
- Fully compliant with the `awesome-phone-call-agents` repository standard:
  - `SKILL.md`: Metadata, triggers, input/output schemas, and multi-step prompt definitions.
  - `references/safety.md`: FERPA compliance rules, non-disclosure of disability/medical records, and authentication safeguards.
  - `references/examples.md`: Complete transcripts and operational JSON payloads.

---

## 4. How We Built It

- **Backend**: FastAPI with Python 3.14, SQLModel (ORM supporting SQLite & PostgreSQL/Neon), and Pydantic v2.
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide icons, and Axios with real-time SSE polling.
- **AI / Phone Stack**: CALL-E REST API for telephony execution + Google Gemini SDK / Groq for operational planning.
- **Verification & Testing**: Comprehensive 37-test suite covering planning, schemas, verifier logic, escalation formatting, and multi-step workflow execution.

---

## 5. Challenges We Overcame

1. **Handling Telephony Asynchrony**: CALL-E phone calls take variable duration. We engineered a resilient polling state machine with non-blocking lifecycle transitions (`received` $\rightarrow$ `planning` $\rightarrow$ `in_progress` $\rightarrow$ `verifying` $\rightarrow$ `resolved` / `escalated`).
2. **Deterministic Information Extraction**: Voice conversations can be messy. By feeding CALL-E explicit JSON schemas with strict enums, we transformed conversational voice into structured database rows.
3. **FERPA & Institutional Privacy Safeguards**: We implemented hard constraints prohibiting the AI from ever mentioning student disability status or medical records over the phone, enforced via automated test assertions.

---

## 6. Accomplishments We're Proud Of

- **100% Passing Test Suite**: 37 unit and end-to-end integration tests passing with zero errors.
- **Live CALL-E Verification CLI Tool**: `scripts/test_live_calle.py` allows anyone with an API key to dial real phones and observe live evidence verification in seconds.
- **Production-Ready Command Center**: Intuitive UI featuring real-time step timelines, coordination matrices, evidence checklists, and escalation packets.

---

## 7. What We Learned

- **Phone Agents Must Be Operational Executors**: Conversational voice bots are only useful when backed by a closed-loop verification engine that validates facts against institutional ground truth.
- **Multi-Party Coordination is the Killer Phone Use Case**: Human staff spend hours playing phone tag to align three people. An autonomous AI orchestrator can complete 3 sequential phone alignments in under 90 seconds.

---

## 8. What's Next for CampusOps AI

- **Multi-Channel Fallback**: Automatically send SMS/WhatsApp links with calendar invites or affidavit upload forms when phone calls conclude.
- **Enterprise SIS Connectors**: Direct bi-directional sync with Ellucian Banner, Canvas LMS, and Oracle PeopleSoft.
- **Multilingual Regional Voice Models**: Localized voice support in Oshiwambo, Afrikaans, Otjiherero, and Zulu for Southern African institutions.

---

## 9. 3-Minute Video Recording Guide

Follow this exact timestamp plan when recording the submission video:

| Time | Section | Screen Action | Narration Key Points |
|---|---|---|---|
| **0:00 - 0:30** | The Problem & Concept | Show Slide or Intake Portal | "Universities are paralyzed by phone queues and administrative delays. Meet CampusOps AI." |
| **0:30 - 1:15** | Workflow 1: Scholarship Verification | Click "1-Click Scholarship Verification" $\rightarrow$ Observe Timeline | "The agent calls the Financial Aid Office, extracts payment status ($2026-09-18$), and the Evidence Engine verifies with $97\%$ confidence." |
| **1:15 - 2:00** | Workflow 2: 3-Way Coordination | Click "3-Way Coordination" $\rightarrow$ Observe Matrix | "Watch 3 sequential calls coordinate student Maria, Dr. Alweendo, and the Department Office for Tuesday 2:00 PM." |
| **2:00 - 2:35** | Workflow 3: Exception Escalation | Click "Escalation Case" $\rightarrow$ Inspect Brief | "When an income affidavit is missing, CampusOps synthesizes an actionable staff brief with verbatim transcripts." |
| **2:35 - 3:00** | Architecture & Conclusion | Show CLI tool (`test_live_calle.py`) & Skill standard | "Powered by CALL-E and portable agent skills. Transforming institutional phone operations." |
