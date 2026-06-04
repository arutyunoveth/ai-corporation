# Entity Catalog Sprint 9A

## Canonical IDs

- `vendor_connector_set_id` => `VCS-YYYY-NNNNNN`
- `vendor_connector_id` => `VC-YYYY-NNNNNN`
- `action_console_set_id` => `ACS-YYYY-NNNNNN`
- `action_console_id` => `AC-YYYY-NNNNNN`
- `external_execution_set_id` => `XES-YYYY-NNNNNN`
- `external_execution_id` => `XE-YYYY-NNNNNN`

## Architectural Invariants

1. Vendor connector profile remains separate from generic connector registry.
2. Action console remains separate from operator sessions.
3. External execution remains separate from internal execution ledger.
4. External execution requires gateway-ready upstream context.
5. Event trace is mandatory for every business-significant transition.

## M-060 Entities

### `vendor_connector_set`

- `vendor_connector_set_id`
- `scope_type`
- `scope_ref`
- `profile_status`
- `created_at`
- `updated_at`

### `vendor_connector_record`

- `vendor_connector_id`
- `vendor_connector_set_id`
- `connector_registry_id`
- `vendor_code`
- `vendor_status`
- `created_at`
- `updated_at`

### `vendor_connector_capability`

- `vendor_connector_id`
- `capability_code`
- `capability_status`
- `notes`
- `created_at`

## M-061 Entities

### `action_console_set`

- `action_console_set_id`
- `scope_type`
- `scope_ref`
- `console_status`
- `created_at`
- `updated_at`

### `action_console_record`

- `action_console_id`
- `action_console_set_id`
- `summary_text`
- `created_at`
- `updated_at`

### `action_console_item`

- `action_console_id`
- `item_code`
- `item_type`
- `priority`
- `source_ref`
- `item_text`
- `created_at`

## M-062 Entities

### `external_execution_set`

- `external_execution_set_id`
- `scope_type`
- `scope_ref`
- `gateway_status`
- `created_at`
- `updated_at`

### `external_execution_record`

- `external_execution_id`
- `external_execution_set_id`
- `integration_task_id`
- `execution_ledger_id`
- `gateway_action_type`
- `request_payload_json`
- `execution_status`
- `started_at`
- `finished_at`
- `created_at`
- `updated_at`

### `external_execution_result`

- `external_execution_id`
- `result_code`
- `result_summary`
- `response_payload_json`
- `artifact_ref`
- `created_at`

## Enums

### `VendorProfileStatus`

- `BUILT`
- `FAILED`
- `STALE`

### `VendorStatus`

- `ACTIVE`
- `INACTIVE`
- `DISABLED`

### `CapabilityStatus`

- `SUPPORTED`
- `LIMITED`
- `UNSUPPORTED`

### `ActionConsoleStatus`

- `BUILT`
- `FAILED`
- `STALE`

### `ActionConsoleItemType`

- `QUEUE`
- `TASK`
- `SESSION`
- `EXECUTION`
- `ALERT`
- `OTHER`

### `ActionConsolePriority`

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

### `ExternalGatewayStatus`

- `BUILT`
- `ACTIVE`
- `FAILED`
- `STALE`

### `GatewayActionType`

- `SEND`
- `SYNC`
- `EXPORT`
- `FOLLOW_UP`
- `OTHER`

### `ExternalExecutionStatus`

- `STARTED`
- `SUCCEEDED`
- `FAILED`
- `CANCELLED`

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

## Event Contracts

- `vendor_connector_profile_built`
- `vendor_connector_profile_failed`
- `action_console_built`
- `action_console_item_recorded`
- `action_console_failed`
- `external_execution_built`
- `external_execution_started`
- `external_execution_succeeded`
- `external_execution_failed`

## Migration Order

- `057_create_vendor_connector_profiles`
- `058_create_action_console`
- `059_create_external_execution`
