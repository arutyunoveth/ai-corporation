# Sprint 8A Technical Spec
## Модули M-054, M-055, M-056

## 1. Назначение
Sprint 8A строит слой connectors / UX / semi-autonomous control foundation поверх уже готового:
- Sprint 1 foundation
- Sprint 2A intake foundation
- Sprint 2B analysis foundation
- Sprint 3A supplier-side foundation
- Sprint 3B supplier quality layer
- Sprint 4A economics layer
- Sprint 4B risk + approval layer
- Sprint 5A bid-prep foundation
- Sprint 5B submission layer
- Sprint 6A execution / delivery contour
- Sprint 6B closure / incident / KPI contour
- Sprint 7A operational intelligence / archive export / learning automation
- Sprint 7B optimization / orchestration layer

Модули:
- M-054 Connector Registry & Sync Backbone
- M-055 Operator Workspace Feed API
- M-056 Controlled Action Queue

## 2. Результат Sprint 8A
К концу Sprint 8A система должна уметь:
1. хранить formal connector definitions и sync runs;
2. связывать внешние источники/каналы с внутренними workflow scopes;
3. собирать operator workspace feed как API-ready persisted layer;
4. формировать controlled action queue на основе copilot/workflow context;
5. отделять system-suggested actions от human-approved execution;
6. писать event/audit trace;
7. подготовить foundation для следующего слоя:
   - richer external integrations
   - operator UI
   - gated semi-autonomous execution

Итог:
из orchestration package получить connectors + workspace + controlled action queue.

## 3. Что не входит
- real browser automation
- uncontrolled auto-execution
- full frontend app
- external credential vault
- vendor-specific deep connector logic
- background job platform overhaul

## 4. Зависимости
Использует:
- deal / event log / decision journal / document store
- workflow runs from Sprint 7B
- optimization recommendations from Sprint 7B
- copilot feed from Sprint 7B
- prior deal/execution/submission context as source scopes

## 5. Архитектурные принципы
1. Connector metadata and sync runs are persisted objects.
2. Workspace feed is distinct from copilot feed.
3. Action queue is distinct from actual execution records.
4. Human approval and system suggestion remain separate.
5. Every business-significant run emits events.

# 6. M-054 — Connector Registry & Sync Backbone

## Назначение
Persist connector definitions and sync runs for future integrations.

## Сущности
- connector_registry_sets
- connector_registry_records
- connector_sync_runs

## Таблицы
### connector_registry_sets
- id
- connector_registry_set_id (`CRG-YYYY-NNNNNN`)
- scope_type (`GLOBAL|DEAL|PIPELINE|EXECUTION`)
- scope_ref
- registry_status (`BUILT|FAILED|STALE`)
- created_at
- updated_at

### connector_registry_records
- id
- connector_registry_id (`CRR-YYYY-NNNNNN`)
- connector_registry_set_id
- connector_code
- connector_type (`EMAIL|PORTAL|CRM|DRIVE|SHEETS|OTHER`)
- connector_status (`ACTIVE|INACTIVE|DISABLED`)
- created_at
- updated_at

### connector_sync_runs
- id
- connector_sync_run_id (`CSR-YYYY-NNNNNN`)
- connector_registry_id
- sync_status (`STARTED|SUCCEEDED|FAILED|SKIPPED`)
- sync_summary
- started_at
- finished_at
- created_at

## API
- POST /connectors/build
- POST /connectors/sync
- GET /connectors/{connector_registry_set_id}
- GET /connectors?scope_type=...&scope_ref=...
- GET /connectors/records/{connector_registry_id}

## Events
- connector_registry_built
- connector_sync_started
- connector_sync_finished
- connector_sync_failed

# 7. M-055 — Operator Workspace Feed API

## Назначение
Build operator workspace feed as higher-level persisted layer over copilot and orchestration context.

## Сущности
- workspace_feed_sets
- workspace_feed_records
- workspace_feed_items

## Таблицы
### workspace_feed_sets
- id
- workspace_feed_set_id (`WFS-YYYY-NNNNNN`)
- scope_type (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- scope_ref
- workspace_status (`BUILT|FAILED|STALE`)
- created_at
- updated_at

### workspace_feed_records
- id
- workspace_feed_id (`WF-YYYY-NNNNNN`)
- workspace_feed_set_id
- summary_text
- created_at
- updated_at

### workspace_feed_items
- id
- workspace_feed_id
- item_code
- item_type (`TASK|ALERT|SUGGESTION|DECISION|FOLLOW_UP|OTHER`)
- priority (`LOW|MEDIUM|HIGH|CRITICAL`)
- item_text
- source_ref
- created_at

## API
- POST /workspace-feed/build
- GET /workspace-feed/{workspace_feed_set_id}
- GET /workspace-feed?scope_type=...&scope_ref=...
- GET /workspace-feed/records/{workspace_feed_id}

## Events
- workspace_feed_built
- workspace_feed_item_recorded
- workspace_feed_failed

# 8. M-056 — Controlled Action Queue

## Назначение
Persist queued actions that may later be executed through gated semi-autonomous control.

## Сущности
- action_queue_sets
- action_queue_records
- action_queue_approvals

## Таблицы
### action_queue_sets
- id
- action_queue_set_id (`AQS-YYYY-NNNNNN`)
- scope_type (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- scope_ref
- queue_status (`BUILT|ACTIVE|FAILED|STALE`)
- created_at
- updated_at

### action_queue_records
- id
- action_queue_id (`AQ-YYYY-NNNNNN`)
- action_queue_set_id
- action_code
- action_type (`EMAIL_DRAFT|FOLLOW_UP|SYNC|REBUILD|ESCALATE|OTHER`)
- action_status (`PENDING|APPROVED|REJECTED|EXECUTED|CANCELLED`)
- action_text
- source_ref
- created_at
- updated_at

### action_queue_approvals
- id
- action_queue_id
- approval_status (`PENDING|APPROVED|REJECTED`)
- approved_by_ref
- rationale
- created_at
- updated_at

## API
- POST /action-queue/build
- POST /action-queue/approve
- GET /action-queue/{action_queue_set_id}
- GET /action-queue?scope_type=...&scope_ref=...
- GET /action-queue/records/{action_queue_id}

## Events
- action_queue_built
- action_queue_item_recorded
- action_queue_approved
- action_queue_rejected
- action_queue_failed

# 9. Общие enums Sprint 8A

## ConnectorScopeType
- GLOBAL
- DEAL
- PIPELINE
- EXECUTION

## ConnectorType
- EMAIL
- PORTAL
- CRM
- DRIVE
- SHEETS
- OTHER

## ConnectorRegistryStatus
- BUILT
- FAILED
- STALE

## ConnectorStatus
- ACTIVE
- INACTIVE
- DISABLED

## ConnectorSyncStatus
- STARTED
- SUCCEEDED
- FAILED
- SKIPPED

## WorkspaceScopeType
- DEAL
- PIPELINE
- EXECUTION
- PORTFOLIO

## WorkspaceStatus
- BUILT
- FAILED
- STALE

## WorkspaceItemType
- TASK
- ALERT
- SUGGESTION
- DECISION
- FOLLOW_UP
- OTHER

## WorkspacePriority
- LOW
- MEDIUM
- HIGH
- CRITICAL

## ActionQueueStatus
- BUILT
- ACTIVE
- FAILED
- STALE

## ActionType
- EMAIL_DRAFT
- FOLLOW_UP
- SYNC
- REBUILD
- ESCALATE
- OTHER

## ActionExecutionStatus
- PENDING
- APPROVED
- REJECTED
- EXECUTED
- CANCELLED

## ApprovalStatus
- PENDING
- APPROVED
- REJECTED

# 10. Поток Sprint 8A
workflow + optimization + copilot
  -> connector registry / sync backbone
  -> operator workspace feed
  -> controlled action queue
  -> ready for semi-autonomous execution layer

# 11. Migration order Sprint 8A
- Migration 051: connector registry tables
- Migration 052: workspace feed tables
- Migration 053: action queue tables

# 12. Acceptance criteria по всему Sprint 8A
1. connector registry formalized;
2. workspace feed formalized;
3. controlled action queue formalized;
4. all outputs queryable and linked to scope;
5. event trace preserved;
6. foundation ready for richer integrations / UI / gated execution.
