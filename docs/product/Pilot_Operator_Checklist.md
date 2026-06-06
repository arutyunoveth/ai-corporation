# Pilot Operator Checklist

## Purpose

This checklist makes the controlled commercial pilot workflow repeatable without opening autonomous or external execution.

## Workflow States

| State | How it is entered | Operator expectation | Allowed next step |
| --- | --- | --- | --- |
| `imported` | Tender/demo materials are loaded into the repository | Confirm source package is internal or approved synthetic pilot data | run pre-bid analysis |
| `analyzed` | Pre-bid report, requirements, risks, and decision draft are produced | Review artifacts before any commercial follow-up | `needs_review`, `collect_tkp`, or `rejected` |
| `needs_review` | Operator records `needs_more_review` in the console | Capture missing context or unresolved interpretation | complete manual review, then resume internal analysis |
| `collect_tkp` | Operator records `collect_tkp` or workspace `tkp_needed` | Prepare manual supplier/TKP collection package | register manual TKP batch |
| `economics_review` | Manual TKP batch is registered and economics/readiness package is built | Review cost, margin, cash-gap, and quote comparison | `economics_reviewed` or `rejected` |
| `bid_readiness_review` | Workspace package and readiness snapshot are available | Confirm document completeness and remaining blockers | `ready_for_human_submission` or `needs_review` |
| `ready_for_human_submission` | Operator records final internal action in workspace | This is an internal readiness marker only | manual human-controlled external handling outside the repository |
| `rejected` | Operator records `rejected` in the console | Stop pilot progression for this scenario | archive or rework internally |

## Repeatable Pilot Sequence

1. Load one approved controlled-pilot scenario.
2. Confirm the deal is `imported`.
3. Run the demo/pre-bid flow and verify the deal is `analyzed`.
4. Review:
   - tender card
   - pre-bid report
   - requirements
   - risks
   - runtime trace metadata
5. If material gaps remain, record `needs_more_review`.
6. If supplier/commercial inputs are required, record `collect_tkp`.
7. Generate supplier request draft for manual handling only.
8. Register manual TKP batch after human-collected quote data is available.
9. Build the commercial readiness package.
10. Review economics and bid-readiness artifacts.
11. Record `economics_reviewed` when internal checks are complete.
12. Record `ready_for_human_submission` only after explicit human sign-off and only as an internal state.

## Endpoint Map

- `POST /commercial-prebid-demo/run`
- `GET /commercial-console`
- `GET /commercial-console/deals/{deal_id}`
- `GET /commercial-console/deals/{deal_id}/report`
- `GET /commercial-console/deals/{deal_id}/requirements`
- `GET /commercial-console/deals/{deal_id}/risks`
- `GET /commercial-console/deals/{deal_id}/runtime-traces`
- `POST /commercial-console/deals/{deal_id}/actions`
- `POST /commercial-workspace/{deal_id}/supplier-request-draft`
- `POST /commercial-workspace/{deal_id}/tkp/register-manual-batch`
- `POST /commercial-workspace/{deal_id}/readiness/build`
- `POST /commercial-workspace/{deal_id}/actions`

## Hard Boundaries

- Never treat `ready_for_human_submission` as actual submission.
- Never send supplier messages automatically from the repository.
- Never log into a procurement platform from this workflow.
- Never execute EDS/signature actions.
- Never allow the repository to make final legal or commercial decisions without a human.
