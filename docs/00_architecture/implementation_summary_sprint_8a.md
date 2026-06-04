# Sprint 8A Implementation Summary

## Scope

Sprint 8A adds the operator-side control foundation on top of Sprint 7B:

- `M-054` Connector Registry & Sync Backbone
- `M-055` Operator Workspace Feed API
- `M-056` Controlled Action Queue

This layer reuses persisted workflow, optimization, and copilot outputs instead of refactoring them.

## Reused Foundation

- Sprint 7A dashboard, archive export, and learning automation records
- Sprint 7B workflow runs, optimization recommendations, and copilot feeds
- existing event log backbone
- existing business ID generator pattern
- existing append-only set/record/item modeling style

## Added Entities

- `connector_registry_sets`
- `connector_registry_records`
- `connector_sync_runs`
- `workspace_feed_sets`
- `workspace_feed_records`
- `workspace_feed_items`
- `action_queue_sets`
- `action_queue_records`
- `action_queue_approvals`

## Canonical IDs

- `connector_registry_set_id` -> `CRG-YYYY-NNNNNN`
- `connector_registry_id` -> `CRR-YYYY-NNNNNN`
- `connector_sync_run_id` -> `CSR-YYYY-NNNNNN`
- `workspace_feed_set_id` -> `WFS-YYYY-NNNNNN`
- `workspace_feed_id` -> `WF-YYYY-NNNNNN`
- `action_queue_set_id` -> `AQS-YYYY-NNNNNN`
- `action_queue_id` -> `AQ-YYYY-NNNNNN`

## Endpoints

- `POST /connectors/build`
- `POST /connectors/sync`
- `GET /connectors/{connector_registry_set_id}`
- `GET /connectors`
- `GET /connectors/records/{connector_registry_id}`
- `POST /workspace-feed/build`
- `GET /workspace-feed/{workspace_feed_set_id}`
- `GET /workspace-feed`
- `GET /workspace-feed/records/{workspace_feed_id}`
- `POST /action-queue/build`
- `POST /action-queue/approve`
- `GET /action-queue/{action_queue_set_id}`
- `GET /action-queue`
- `GET /action-queue/records/{action_queue_id}`

## Events

- `connector_registry_built`
- `connector_sync_started`
- `connector_sync_finished`
- `connector_sync_failed`
- `workspace_feed_built`
- `workspace_feed_item_recorded`
- `workspace_feed_failed`
- `action_queue_built`
- `action_queue_item_recorded`
- `action_queue_approved`
- `action_queue_rejected`
- `action_queue_failed`

## Assumptions / Detected Mismatches

- Sprint 8A docs define `ApprovalStatus` with `PENDING/APPROVED/REJECTED`, but the repository already has Sprint 4B `ApprovalStatus` with a different meaning. Minimal-invasive solution: Sprint 8A uses a dedicated internal enum `QueueApprovalStatus` while keeping the public field name `approval_status`.
- `workspace_feed` is intentionally separate from `copilot_feed`; it is implemented as a persisted operator-facing projection over upstream persisted workflow, optimization, and copilot context.
- `/connectors/sync` is implemented as an explicit sync of one `connector_registry_id` at a time so each sync run remains directly auditable.
- Approved queue items are not auto-executed in this sprint; approvals remain separate from future execution records.

## Planned Migration Order

- `051_create_connector_registry`
- `052_create_workspace_feed`
- `053_create_action_queue`

## Test Coverage

- connector registry build
- connector sync run persistence
- workspace feed build and item persistence
- action queue build and approval persistence
- scope/deal linkage
- key Sprint 8A event trace
- workspace/action prerequisite paths
- append-only rerun behavior

## Known Limitations

- Connector sync is rule-based and local; it does not yet perform real external connector IO.
- Workspace feed is a persisted projection, not a real-time UI session state.
- Action queue approvals do not trigger execution; execution remains a future contour.

## Next Step

Sprint 8B can build the real operator UI / semi-autonomous control surface on top of the persisted connector, workspace, and controlled-action foundation.
