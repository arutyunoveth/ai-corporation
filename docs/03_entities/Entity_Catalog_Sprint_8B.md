# Entity Catalog Sprint 8B
## Модули M-057, M-058, M-059

## 1. Назначение
Единый каталог сущностей Sprint 8B.

## 2. Scope
Покрывает:
- M-057 Integration Task Adapter Layer
- M-058 Operator Session Workspace
- M-059 Gated Action Execution Ledger

Опирается на:
- connector_registry_set
- workspace_feed_set
- action_queue_set
- workflow_run_set
- event_record

## 3. Canonical refs
- integration_task_set_id => ITS-YYYY-NNNNNN
- integration_task_id => IT-YYYY-NNNNNN
- operator_session_set_id => OSS-YYYY-NNNNNN
- operator_session_id => OS-YYYY-NNNNNN
- execution_ledger_set_id => ELS-YYYY-NNNNNN
- execution_ledger_id => EL-YYYY-NNNNNN

## 4. Инварианты
1. Integration tasks must be traceable to approved queue/context.
2. Operator sessions are distinct from workspace feed snapshots.
3. Execution ledger entries require approved action context.
4. Execution results are append-only.
5. Human approval remains separate from execution result.

# 5. M-057 entities
## integration_task_set
- id
- integration_task_set_id
- scope_type
- scope_ref
- task_status
- created_at
- updated_at

## integration_task_record
- id
- integration_task_id
- integration_task_set_id
- connector_registry_id
- action_queue_id
- task_type
- task_payload_json
- created_at
- updated_at

## integration_task_binding
- id
- integration_task_id
- source_ref
- binding_type
- created_at

# 6. M-058 entities
## operator_session_set
- id
- operator_session_set_id
- scope_type
- scope_ref
- session_status
- created_at
- updated_at

## operator_session_record
- id
- operator_session_id
- operator_session_set_id
- opened_by_ref
- summary_text
- created_at
- updated_at

## operator_session_item
- id
- operator_session_id
- item_code
- item_type
- source_ref
- item_status
- created_at
- updated_at

# 7. M-059 entities
## execution_ledger_set
- id
- execution_ledger_set_id
- scope_type
- scope_ref
- ledger_status
- created_at
- updated_at

## execution_ledger_record
- id
- execution_ledger_id
- execution_ledger_set_id
- action_queue_id
- integration_task_id
- execution_status
- started_at
- finished_at
- created_at
- updated_at

## execution_result_record
- id
- execution_ledger_id
- result_code
- result_summary
- artifact_ref
- created_at

# 8. Enums
IntegrationTaskStatus:
- BUILT
- FAILED
- STALE
- READY

IntegrationTaskType:
- EMAIL_SEND
- SYNC_PULL
- SYNC_PUSH
- FOLLOW_UP
- EXPORT
- OTHER

OperatorSessionStatus:
- OPEN
- CLOSED
- STALE

OperatorSessionItemType:
- QUEUE_ITEM
- TASK
- ALERT
- DECISION
- OTHER

OperatorSessionItemStatus:
- VISIBLE
- ACKNOWLEDGED
- HIDDEN
- DONE

ExecutionLedgerStatus:
- BUILT
- ACTIVE
- FAILED
- STALE

ExecutionStatus:
- STARTED
- SUCCEEDED
- FAILED
- CANCELLED

# 9. DTO contracts
BuildIntegrationTasksRequest:
{
  "scope_type": "EXECUTION",
  "scope_ref": "ECS-2026-000001"
}

BuildOperatorSessionRequest:
{
  "scope_type": "DEAL",
  "scope_ref": "DL-2026-000001",
  "opened_by_ref": "OWNER"
}

BuildExecutionLedgerRequest:
{
  "scope_type": "EXECUTION",
  "scope_ref": "ECS-2026-000001"
}

StartExecutionLedgerRequest:
{
  "execution_ledger_id": "EL-2026-000001"
}

# 10. Event contracts
- integration_task_built
- integration_task_failed
- operator_session_built
- operator_session_item_recorded
- operator_session_item_acknowledged
- operator_session_failed
- execution_ledger_built
- execution_ledger_started
- execution_ledger_succeeded
- execution_ledger_failed

# 11. Migration order
- 054 integration tasks
- 055 operator sessions
- 056 execution ledger

# 12. Anti-chaos rules
1. Do not auto-create execution ledger entries for unapproved queue items.
2. Do not merge operator sessions with workspace feed.
3. Do not merge execution ledger with action queue.
4. Do not overwrite prior execution results.
