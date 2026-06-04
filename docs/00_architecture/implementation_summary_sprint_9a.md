# Sprint 9A Implementation Summary

## Scope

Sprint 9A adds the first formal external-vendor execution contour on top of Sprint 8A and Sprint 8B:

- `M-060` Vendor Connector Profiles
- `M-061` Operator Action Console Backbone
- `M-062` External Execution Gateway Ledger

This sprint keeps vendor-facing profiles, operator-facing console state, and external execution results separate from generic connectors, operator sessions, and internal execution ledger records.

## Reused Foundation

- Sprint 8A connector registry, workspace feed, and controlled action queue
- Sprint 8B integration tasks, operator sessions, and internal execution ledger
- existing event log backbone
- existing application-side business ID generation pattern
- existing append-only set / record / child-row architecture

## Added Entities

- `vendor_connector_sets`
- `vendor_connector_records`
- `vendor_connector_capabilities`
- `action_console_sets`
- `action_console_records`
- `action_console_items`
- `external_execution_sets`
- `external_execution_records`
- `external_execution_results`

## Canonical IDs

- `vendor_connector_set_id` -> `VCS-YYYY-NNNNNN`
- `vendor_connector_id` -> `VC-YYYY-NNNNNN`
- `action_console_set_id` -> `ACS-YYYY-NNNNNN`
- `action_console_id` -> `AC-YYYY-NNNNNN`
- `external_execution_set_id` -> `XES-YYYY-NNNNNN`
- `external_execution_id` -> `XE-YYYY-NNNNNN`

## Endpoints

- `POST /vendor-connectors/build`
- `GET /vendor-connectors/{vendor_connector_set_id}`
- `GET /vendor-connectors`
- `GET /vendor-connectors/records/{vendor_connector_id}`
- `POST /action-console/build`
- `GET /action-console/{action_console_set_id}`
- `GET /action-console`
- `GET /action-console/records/{action_console_id}`
- `POST /external-execution/build`
- `POST /external-execution/start`
- `GET /external-execution/{external_execution_set_id}`
- `GET /external-execution`
- `GET /external-execution/records/{external_execution_id}`

## Events

- `vendor_connector_profile_built`
- `vendor_connector_profile_failed`
- `action_console_built`
- `action_console_item_recorded`
- `action_console_failed`
- `external_execution_built`
- `external_execution_started`
- `external_execution_succeeded`
- `external_execution_failed`

## Assumptions / Detected Mismatches

- Sprint 9A source documents were provided from `Downloads/AI-Corporation`, so repo-local copies were synced into `docs/`.
- Existing scope vocabularies already match Sprint 9A needs. Minimal-invasive solution: reuse `ConnectorScopeType` for vendor connector profiles and `WorkspaceScopeType` for action console / external execution.
- Sprint 9A docs define `build` and `start` for external execution but do not define a separate pre-start status before `STARTED`. Minimal-invasive solution: build persists candidate gateway rows with `STARTED` and `null` timestamps; `/external-execution/start` writes the real execution timestamps and append-only result rows.
- Child rows `vendor_connector_capabilities`, `action_console_items`, and `external_execution_results` do not define canonical business IDs, so they continue to use internal UUID PKs.
- External execution is intentionally separated from internal execution ledger. Start requires a succeeded internal execution record instead of silently auto-running from approval state alone.

## Migrations

- `057_create_vendor_connector_profiles`
- `058_create_action_console`
- `059_create_external_execution`

## Test Coverage

- vendor connector profile build
- capability row persistence
- action console build
- action console item persistence
- external execution set build
- external execution result persistence
- scope / upstream linkage
- key event trace
- succeeded-internal-ledger prerequisite
- append-only rerun behavior

## Known Limitations

- Vendor connector profiles remain rule-based overlays above generic connector registry records, not vendor SDK descriptors.
- Action console is a persisted operator-facing snapshot contour, not a real-time UI state manager.
- External execution remains a controlled gateway ledger and simulated outcome layer; it does not yet perform deep vendor-specific automation or portal robotics.

## Next Step

Sprint 9B can extend this contour into vendor-specific adapters, richer policy gating, and deeper operator UX on top of the formal vendor profile, action console, and external execution package.
