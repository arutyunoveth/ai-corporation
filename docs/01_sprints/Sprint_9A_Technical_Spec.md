# Sprint 9A Technical Spec

## Scope

Sprint 9A formalizes the first external-vendor execution contour above Sprint 8A and Sprint 8B:

- `M-060` Vendor Connector Profiles
- `M-061` Operator Action Console Backbone
- `M-062` External Execution Gateway Ledger

Resulting package:

- `vendor connector profiles`
- `action console`
- `external execution gateway ledger`

## Reused Dependencies

- Sprint 8A connector registry, sync runs, workspace feed, and controlled action queue
- Sprint 8B integration tasks, operator sessions, and internal execution ledger
- generic event log / audit trail foundation

## Architectural Rules

1. Vendor connector profile is distinct from generic connector registry.
2. Action console is distinct from operator session.
3. External execution gateway is distinct from internal execution ledger.
4. Request intent and external response must stay separated.
5. Every business-significant step emits events.

## M-060 Vendor Connector Profiles

### Tables

#### `vendor_connector_sets`

- `vendor_connector_set_id` (`VCS-YYYY-NNNNNN`)
- `scope_type` (`GLOBAL|DEAL|PIPELINE|EXECUTION`)
- `scope_ref`
- `profile_status` (`BUILT|FAILED|STALE`)
- `created_at`
- `updated_at`

#### `vendor_connector_records`

- `vendor_connector_id` (`VC-YYYY-NNNNNN`)
- `vendor_connector_set_id`
- `connector_registry_id`
- `vendor_code`
- `vendor_status` (`ACTIVE|INACTIVE|DISABLED`)
- `created_at`
- `updated_at`

#### `vendor_connector_capabilities`

- `vendor_connector_id`
- `capability_code`
- `capability_status` (`SUPPORTED|LIMITED|UNSUPPORTED`)
- `notes`
- `created_at`

### API

- `POST /vendor-connectors/build`
- `GET /vendor-connectors/{vendor_connector_set_id}`
- `GET /vendor-connectors?scope_type=...&scope_ref=...`
- `GET /vendor-connectors/records/{vendor_connector_id}`

### Events

- `vendor_connector_profile_built`
- `vendor_connector_profile_failed`

## M-061 Operator Action Console Backbone

### Tables

#### `action_console_sets`

- `action_console_set_id` (`ACS-YYYY-NNNNNN`)
- `scope_type` (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- `scope_ref`
- `console_status` (`BUILT|FAILED|STALE`)
- `created_at`
- `updated_at`

#### `action_console_records`

- `action_console_id` (`AC-YYYY-NNNNNN`)
- `action_console_set_id`
- `summary_text`
- `created_at`
- `updated_at`

#### `action_console_items`

- `action_console_id`
- `item_code`
- `item_type` (`QUEUE|TASK|SESSION|EXECUTION|ALERT|OTHER`)
- `priority` (`LOW|MEDIUM|HIGH|CRITICAL`)
- `source_ref`
- `item_text`
- `created_at`

### API

- `POST /action-console/build`
- `GET /action-console/{action_console_set_id}`
- `GET /action-console?scope_type=...&scope_ref=...`
- `GET /action-console/records/{action_console_id}`

### Events

- `action_console_built`
- `action_console_item_recorded`
- `action_console_failed`

## M-062 External Execution Gateway Ledger

### Tables

#### `external_execution_sets`

- `external_execution_set_id` (`XES-YYYY-NNNNNN`)
- `scope_type` (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- `scope_ref`
- `gateway_status` (`BUILT|ACTIVE|FAILED|STALE`)
- `created_at`
- `updated_at`

#### `external_execution_records`

- `external_execution_id` (`XE-YYYY-NNNNNN`)
- `external_execution_set_id`
- `integration_task_id`
- `execution_ledger_id`
- `gateway_action_type` (`SEND|SYNC|EXPORT|FOLLOW_UP|OTHER`)
- `request_payload_json`
- `execution_status` (`STARTED|SUCCEEDED|FAILED|CANCELLED`)
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

#### `external_execution_results`

- `external_execution_id`
- `result_code`
- `result_summary`
- `response_payload_json`
- `artifact_ref`
- `created_at`

### API

- `POST /external-execution/build`
- `POST /external-execution/start`
- `GET /external-execution/{external_execution_set_id}`
- `GET /external-execution?scope_type=...&scope_ref=...`
- `GET /external-execution/records/{external_execution_id}`

### Events

- `external_execution_built`
- `external_execution_started`
- `external_execution_succeeded`
- `external_execution_failed`

## DTO Contracts

### `BuildVendorConnectorProfilesRequest`

```json
{
  "scope_type": "GLOBAL",
  "scope_ref": "GLOBAL"
}
```

### `BuildActionConsoleRequest`

```json
{
  "scope_type": "EXECUTION",
  "scope_ref": "ECS-2026-000001"
}
```

### `BuildExternalExecutionRequest`

```json
{
  "scope_type": "EXECUTION",
  "scope_ref": "ECS-2026-000001"
}
```

### `StartExternalExecutionRequest`

```json
{
  "external_execution_id": "XE-2026-000001"
}
```

## Acceptance

1. Vendor connector profiles are persisted and queryable.
2. Action console snapshots are persisted separately from operator sessions.
3. External execution gateway rows are formalized separately from internal execution ledger.
4. External execution start requires proper upstream execution context.
5. Event trace is preserved for all business-significant steps.
