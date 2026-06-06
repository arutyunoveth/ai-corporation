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

## Controls

- internal only
- event/decision logs recorded
- no external messages
- no submission
- no final autonomous decision
