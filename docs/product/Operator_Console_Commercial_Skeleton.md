# Operator Console Commercial Skeleton

## Goal

Provide a minimal operator-facing commercial review surface without opening external execution.

## Views

- `/commercial-console`
- `/commercial-console/deals/{deal_id}`
- `/commercial-console/deals/{deal_id}/report`
- `/commercial-console/deals/{deal_id}/requirements`
- `/commercial-console/deals/{deal_id}/risks`
- `/commercial-console/deals/{deal_id}/runtime-traces`
- `/commercial-console/deals/{deal_id}/decision`

## Actions

`POST /commercial-console/deals/{deal_id}/actions`

Supported actions:

- `rejected`
- `needs_more_review`
- `collect_tkp`
- `prepare_bid_draft`

## Workflow Coverage

The console anchors the human-control portion of the controlled pilot workflow:

- `imported` after the deal enters the repository
- `analyzed` after the pre-bid report and trace artifacts are built
- `needs_review` through `needs_more_review`
- `collect_tkp` through `collect_tkp`
- `rejected` through `rejected`

Downstream pilot states remain internal-only and are completed through the commercial workspace:

- `economics_review`
- `bid_readiness_review`
- `ready_for_human_submission`

`prepare_bid_draft` is an internal drafting marker. It is not submission authority.

## Controls

- internal only
- event/decision logs recorded
- no external messages
- no submission
- no final autonomous decision
- no production auth added in this phase
