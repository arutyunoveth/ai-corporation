# Pilot Operator Error Handling

## Purpose

This guide defines how operators handle controlled-pilot workflow friction without expanding scope or bypassing Human Control Policy.

## Severity Levels

| Severity | Meaning | Required action |
| --- | --- | --- |
| `low` | Documentation or presentation issue | note in pilot log and continue if core artifacts remain trustworthy |
| `medium` | Internal artifact inconsistency or incomplete analysis | stop at the current gate, record `needs_more_review`, and fix before continuing |
| `high` | Readiness/economics/risk output is missing or invalid | do not advance to `ready_for_human_submission` until corrected |
| `critical` | Any sign of external execution, uncontrolled output, or policy breach | stop the pilot immediately and escalate |

## Common Cases

### Demo or Scenario Load Failure

- Confirm the scenario fixture exists in `fixtures/pilot_tenders/`.
- Re-run the scenario in `stub` mode only.
- If the scenario still fails, stop and log a `medium` issue.

### Missing Requirements or Risk Artifacts

- Do not improvise automated follow-up actions.
- Record `needs_more_review`.
- Re-check source inputs and rebuild the analysis only after the source package is corrected.

### Manual TKP Data Is Incomplete

- Keep the deal in `collect_tkp`.
- Do not mark `tkp_received` until supplier/quote inputs are complete and human-verified.
- Do not generate or send supplier outreach from the repository.

### Economics or Readiness Output Looks Incorrect

- Pause at `economics_review` or `bid_readiness_review`.
- Rebuild the readiness package after correcting the manual inputs.
- Do not record `ready_for_human_submission` until the operator can explain the result.

### LLM Output Fails Validation

- Keep the run in controlled mode.
- Mark the result for manual review.
- Re-run with `stub` provider if the failure blocks pilot rehearsal.
- Never accept invalid output as a final bid recommendation.

### Policy Breach Signal

Examples:

- attempted external message automation
- procurement platform access suggestion
- autonomous submission suggestion
- uncontrolled agent loop suggestion

Required response:

1. Stop the run.
2. Record a `critical` issue.
3. Escalate before any continuation.

## Mandatory Escalation Triggers

- any external execution path appears in logs or proposed actions
- `ready_for_human_submission` is interpreted as actual submission
- missing audit/event records for operator actions
- schema validation fails for provider-backed analysis
- a scenario requires scope beyond the controlled pilot package

## Safe Fallbacks

- use `stub` mode for reproducible rehearsal
- keep all next actions manual and internal
- move adjacent improvements into backlog instead of hot-implementing them during the pilot phase
