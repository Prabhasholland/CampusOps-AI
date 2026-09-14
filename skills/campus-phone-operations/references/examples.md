# Usage Examples & Operational Transcripts

## Example 1: Scholarship Status Verification (Workflow 1)

### Input Request
```text
"A student's scholarship is delayed. Find out the status and resolve it."
Student: Tunga Amutenya (220012345)
Target: Financial Aid Bureau (+264811234567)
```

### Call Execution & Transcript
```text
CALL-E: "Hello, I am the CampusOps Assistant calling on behalf of NUST regarding scholarship verification for student 220012345. May I confirm the application status?"
Officer: "Yes, application SCH-92831 is approved."
CALL-E: "Has payment been disbursed, or is there an expected payment date?"
Officer: "It is currently pending clearance, scheduled for release on September 18th, 2026."
CALL-E: "Is any further action required from the student?"
Officer: "No, everything is in order."
```

### Verified Evidence & Outcome
```json
{
  "application_status": "approved",
  "payment_status": "pending",
  "expected_date": "2026-09-18",
  "additional_action_required": false,
  "confidence": 0.94,
  "status": "VERIFIED",
  "action": "RESOLVE_CASE"
}
```

---

## Example 2: Multi-Party Advising Coordination (Workflow 2)

### Input Request
```text
"Schedule an advising meeting between Maria Nghipandulwa, Dr. Johannes Alweendo, and FCI department office."
```

### Step-by-Step Negotiation
1. **Call 1 (Student Maria Nghipandulwa)**:
   - Proposes: Tuesday 2:00 PM (Preferred), Tuesday 10:00 AM (Backup).
2. **Call 2 (Faculty Dr. Johannes Alweendo)**:
   - Evaluates: Confirms Tuesday 2:00 PM is open in Room 302.
3. **Call 3 (FCI Department Administration)**:
   - Reserves: Calendar slot and entry badge for Tuesday 2:00 PM in Room 302.

### Outcome
```text
Consensus Reached: Tuesday 2:00 PM (Room 302). Case closed as RESOLVED.
```
