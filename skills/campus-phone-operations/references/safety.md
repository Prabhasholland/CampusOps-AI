# Safety Guardrails & Operational Constraints

## 1. Student Privacy & Non-Disclosure (FERPA Compliance)
- **Identity Confirmation Required**: The calling agent must confirm recipient identity prior to disclosing any account specifics.
- **Strictly Protected Attributes**: Never read out loud or disclose a student's ID number, birthdate, disability status, marital status, or residential address.
- **Third-Party Boundary**: If the contact is a parent, sponsor, or third party, the agent must decline to share balance details and direct them to have the registered student contact the university directly.

## 2. Real-World Side Effects & Dialing Limits
- **Side Effect Disclosure**: Placing an outbound phone call initiates a live telephony connection that rings the target recipient.
- **Dry-Run / Mock Path**: When `CALLE_API_KEY` is not set or dry-run mode is enabled, the system uses deterministic mock scenarios (`_MockTransport`) without placing actual phone calls.
- **Retry Bounds**: Calls are capped at a maximum of 3 dialing attempts with backoff intervals. Unanswered calls are never continuously redialed in an infinite loop.

## 3. Phone Number Validation (E.164)
- All numbers must adhere to E.164 international formatting (e.g. `+264811234567` or `+15550100`).
- Fictional standards-reserved numbers or test directory numbers must be used in documentation and samples.

## 4. Cancellation & Manual Override
- Human administrators can intervene at any moment via the Command Center to divert, reassign, or mark an operation handled.
