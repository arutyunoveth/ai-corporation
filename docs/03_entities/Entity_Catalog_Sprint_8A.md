# Entity Catalog Sprint 8A
## Модули M-054, M-055, M-056

## 1. Назначение
Единый каталог сущностей Sprint 8A.

## 2. Scope
Покрывает:
- M-054 Connector Registry & Sync Backbone
- M-055 Operator Workspace Feed API
- M-056 Controlled Action Queue

Опирается на:
- workflow_run_set
- optimization_recommendation_set
- copilot_feed_set
- decision journal
- event_record

## 3. Canonical refs
- connector_registry_set_id => CRG-YYYY-NNNNNN
- connector_registry_id => CRR-YYYY-NNNNNN
- connector_sync_run_id => CSR-YYYY-NNNNNN
- workspace_feed_set_id => WFS-YYYY-NNNNNN
- workspace_feed_id => WF-YYYY-NNNNNN
- action_queue_set_id => AQS-YYYY-NNNNNN
- action_queue_id => AQ-YYYY-NNNNNN

## 4. Инварианты
1. Connector definitions always link to explicit scope.
2. Workspace feed is built from persisted upstream context.
3. Action queue is distinct from actual execution.
4. Approval remains separate from action suggestion.
5. Queue items and approvals are append-only.

# 5. M-054 entities

## connector_registry_set
- id
- connector_registry_set_id
- scope_type
- scope_ref
- registry_status
- created_at
- updated_at

## connector_registry_record
- id
- connector_registry_id
- connector_registry_set_id
- connector_code
- connector_type
- connector_status
- created_at
- updated_at

## connector_sync_run
- id
- connector_sync_run_id
- connector_registry_id
- sync_status
- sync_summary
- started_at
- finished_at
- created_at

# 6. M-055 entities

## workspace_feed_set
- id
- workspace_feed_set_id
- scope_type
- scope_ref
- workspace_status
- created_at
- updated_at

## workspace_feed_record
- id
- workspace_feed_id
- workspace_feed_set_id
- summary_text
- created_at
- updated_at

## workspace_feed_item
- id
- workspace_feed_id
- item_code
- item_type
- priority
- item_text
- source_ref
- created_at

# 7. M-056 entities

## action_queue_set
- id
- action_queue_set_id
- scope_type
- scope_ref
- queue_status
- created_at
- updated_at

## action_queue_record
- id
- action_queue_id
- action_queue_set_id
- action_code
- action_type
- action_status
- action_text
- source_ref
- created_at
- updated_at

## action_queue_approval
- id
- action_queue_id
- approval_status
- approved_by_ref
- rationale
- created_at
- updated_at

# 8. Enums
ConnectorScopeType:
- GLOBAL
- DEAL
- PIPELINE
- EXECUTION

ConnectorType:
- EMAIL
- PORTAL
- CRM
- DRIVE
- SHEETS
- OTHER

ConnectorRegistryStatus:
- BUILT
- FAILED
- STALE

ConnectorStatus:
- ACTIVE
- INACTIVE
- DISABLED

ConnectorSyncStatus:
- STARTED
- SUCCEEDED
- FAILED
- SKIPPED

WorkspaceScopeType:
- DEAL
- PIPELINE
- EXECUTION
- PORTFOLIO

WorkspaceStatus:
- BUILT
- FAILED
- STALE

WorkspaceItemType:
- TASK
- ALERT
- SUGGESTION
- DECISION
- FOLLOW_UP
- OTHER

WorkspacePriority:
- LOW
- MEDIUM
- HIGH
- CRITICAL

ActionQueueStatus:
- BUILT
- ACTIVE
- FAILED
- STALE

ActionType:
- EMAIL_DRAFT
- FOLLOW_UP
- SYNC
- REBUILD
- ESCALATE
- OTHER

ActionExecutionStatus:
- PENDING
- APPROVED
- REJECTED
- EXECUTED
- CANCELLED

ApprovalStatus:
- PENDING
- APPROVED
- REJECTED

# 9. DTO contracts

BuildConnectorRegistryRequest:
{
  "scope_type": "GLOBAL",
  "scope_ref": "GLOBAL"
}

BuildWorkspaceFeedRequest:
{
  "scope_type": "DEAL",
  "scope_ref": "DL-2026-000001"
}

BuildActionQueueRequest:
{
  "scope_type": "EXECUTION",
  "scope_ref": "ECS-2026-000001"
}

ApproveActionQueueItemRequest:
{
  "action_queue_id": "AQ-2026-000001",
  "approval_status": "APPROVED",
  "approved_by_ref": "OWNER",
  "rationale": "Действие подтверждено оператором"
}

# 10. Event contracts
- connector_registry_built
- connector_sync_started
- connector_sync_finished
- connector_sync_failed
- workspace_feed_built
- workspace_feed_item_recorded
- workspace_feed_failed
- action_queue_built
- action_queue_item_recorded
- action_queue_approved
- action_queue_rejected
- action_queue_failed

# 11. Migration order
- 051 connector registry
- 052 workspace feed
- 053 action queue

# 12. Anti-chaos rules
1. Do not treat copilot feed as workspace feed.
2. Do not merge queue items with actual execution records.
3. Do not auto-execute approved actions in this sprint.
4. Do not overwrite prior approvals or queue items.
