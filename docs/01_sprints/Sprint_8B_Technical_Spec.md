# Sprint 8B Technical Spec
## Модули M-057, M-058, M-059

## 1. Назначение
Sprint 8B строит слой richer integrations / operator UX / gated semi-autonomous execution поверх уже готового:
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
- Sprint 8A connectors / workspace / controlled action queue foundation

Модули:
- M-057 Integration Task Adapter Layer
- M-058 Operator Session Workspace
- M-059 Gated Action Execution Ledger

## 2. Результат Sprint 8B
К концу Sprint 8B система должна уметь:
1. связывать action queue items с integration-capable execution tasks;
2. хранить operator session workspace как persisted session contour;
3. запускать только approved actions через gated execution ledger;
4. сохранять execution attempts/results без смешения с queue;
5. фиксировать operator intervention and review points;
6. писать event/audit trace;
7. подготовить foundation для более глубоких external integrations и UI.

Итог:
из connectors + workspace + action queue получить controllable execution package:
integration tasks + operator sessions + gated execution ledger.

## 3. Что не входит
- uncontrolled autonomous execution
- browser robotics
- full frontend SPA
- external secrets vault
- vendor-specific deep connector SDKs
- self-healing automation loops

## 4. Зависимости
Использует:
- connector registry and sync runs from Sprint 8A
- workspace feed from Sprint 8A
- action queue and approvals from Sprint 8A
- workflow / optimization / copilot context from Sprint 7B
- deal/execution/submission context where relevant

## 5. Архитектурные принципы
1. Integration task is distinct from connector registry metadata.
2. Operator session is distinct from workspace feed snapshot.
3. Gated execution ledger is distinct from action queue.
4. Human approval and actual execution result remain separate.
5. Every business-significant run emits events.

# 6. M-057 — Integration Task Adapter Layer

## Назначение
Create execution-ready integration tasks from approved queue items and connector context.

## Сущности
- integration_task_sets
- integration_task_records
- integration_task_bindings

## Таблицы
### integration_task_sets
- id
- integration_task_set_id (`ITS-YYYY-NNNNNN`)
- scope_type (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- scope_ref
- task_status (`BUILT|FAILED|STALE|READY`)
- created_at
- updated_at

### integration_task_records
- id
- integration_task_id (`IT-YYYY-NNNNNN`)
- integration_task_set_id
- connector_registry_id
- action_queue_id
- task_type (`EMAIL_SEND|SYNC_PULL|SYNC_PUSH|FOLLOW_UP|EXPORT|OTHER`)
- task_payload_json
- created_at
- updated_at

### integration_task_bindings
- id
- integration_task_id
- source_ref
- binding_type (`QUEUE|CONNECTOR|WORKSPACE|OTHER`)
- created_at

## API
- POST /integration-tasks/build
- GET /integration-tasks/{integration_task_set_id}
- GET /integration-tasks?scope_type=...&scope_ref=...
- GET /integration-tasks/records/{integration_task_id}

## Events
- integration_task_built
- integration_task_failed

# 7. M-058 — Operator Session Workspace

## Назначение
Persist operator session context for reviewing tasks and executing gated actions.

## Сущности
- operator_session_sets
- operator_session_records
- operator_session_items

## Таблицы
### operator_session_sets
- id
- operator_session_set_id (`OSS-YYYY-NNNNNN`)
- scope_type (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- scope_ref
- session_status (`OPEN|CLOSED|STALE`)
- created_at
- updated_at

### operator_session_records
- id
- operator_session_id (`OS-YYYY-NNNNNN`)
- operator_session_set_id
- opened_by_ref
- summary_text
- created_at
- updated_at

### operator_session_items
- id
- operator_session_id
- item_code
- item_type (`QUEUE_ITEM|TASK|ALERT|DECISION|OTHER`)
- source_ref
- item_status (`VISIBLE|ACKNOWLEDGED|HIDDEN|DONE`)
- created_at
- updated_at

## API
- POST /operator-sessions/build
- POST /operator-sessions/items/ack
- GET /operator-sessions/{operator_session_set_id}
- GET /operator-sessions?scope_type=...&scope_ref=...
- GET /operator-sessions/records/{operator_session_id}

## Events
- operator_session_built
- operator_session_item_recorded
- operator_session_item_acknowledged
- operator_session_failed

# 8. M-059 — Gated Action Execution Ledger

## Назначение
Persist approved action executions and their results without auto-running unapproved actions.

## Сущности
- execution_ledger_sets
- execution_ledger_records
- execution_result_records

## Таблицы
### execution_ledger_sets
- id
- execution_ledger_set_id (`ELS-YYYY-NNNNNN`)
- scope_type (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- scope_ref
- ledger_status (`BUILT|ACTIVE|FAILED|STALE`)
- created_at
- updated_at

### execution_ledger_records
- id
- execution_ledger_id (`EL-YYYY-NNNNNN`)
- execution_ledger_set_id
- action_queue_id
- integration_task_id
- execution_status (`STARTED|SUCCEEDED|FAILED|CANCELLED`)
- started_at
- finished_at
- created_at
- updated_at

### execution_result_records
- id
- execution_ledger_id
- result_code
- result_summary
- artifact_ref
- created_at

## API
- POST /execution-ledger/build
- POST /execution-ledger/start
- GET /execution-ledger/{execution_ledger_set_id}
- GET /execution-ledger?scope_type=...&scope_ref=...
- GET /execution-ledger/records/{execution_ledger_id}

## Events
- execution_ledger_built
- execution_ledger_started
- execution_ledger_succeeded
- execution_ledger_failed

# 9. Общие enums Sprint 8B
- IntegrationTaskStatus = BUILT, FAILED, STALE, READY
- IntegrationTaskType = EMAIL_SEND, SYNC_PULL, SYNC_PUSH, FOLLOW_UP, EXPORT, OTHER
- OperatorSessionStatus = OPEN, CLOSED, STALE
- OperatorSessionItemType = QUEUE_ITEM, TASK, ALERT, DECISION, OTHER
- OperatorSessionItemStatus = VISIBLE, ACKNOWLEDGED, HIDDEN, DONE
- ExecutionLedgerStatus = BUILT, ACTIVE, FAILED, STALE
- ExecutionStatus = STARTED, SUCCEEDED, FAILED, CANCELLED

# 10. Поток Sprint 8B
approved queue items + connector context
  -> integration tasks
  -> operator sessions
  -> gated execution ledger
  -> ready for deeper external execution/UI

# 11. Migration order Sprint 8B
- Migration 054: integration task tables
- Migration 055: operator session tables
- Migration 056: execution ledger tables

# 12. Acceptance criteria по всему Sprint 8B
1. integration tasks formalized;
2. operator sessions formalized;
3. gated execution ledger formalized;
4. outputs linked to scope and upstream refs;
5. event trace preserved;
6. foundation ready for deeper integrations/UI.
