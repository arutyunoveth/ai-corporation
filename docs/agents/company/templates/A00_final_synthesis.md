# A00 Final Synthesis Template

## Agent

A00 — Chief of Staff

## Input

CEO instruction, all specialist readiness reports.

## Required sections

### 1. Specialist summary

Brief summary of each specialist's readiness assessment.

| Agent | Domain | Status |
|-------|--------|--------|
| A10 | Tender Operations | |
| A20 | Finance | |
| A21 | Legal Risk | |
| A42 | QA & Release | |

### 2. Cross-domain risks

Risks that span multiple domains.

### 3. Readiness score

Overall readiness: READY / READY_WITH_FIXES / NOT_READY

### 4. Recommended decision

One of:
- GO_TO_FIRST_PAID_RESTRICTED_PILOT
- GO_WITH_FIXES
- NO_GO_BLOCKED

### 5. Required fixes

List of fixes needed before execution.

### 6. Boundary reminders

- No autonomous execution.
- No cloud dispatch for confidential data.
- No external communication without CEO approval.

## Final status

- CEO_DECISION_REQUIRED
- BLOCKED_NEEDS_INPUT
- ESCALATED_RISK
- NO_DECISION_NEEDED
