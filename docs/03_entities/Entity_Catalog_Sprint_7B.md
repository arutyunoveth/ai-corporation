# Entity Catalog Sprint 7B
## Модули M-051, M-052, M-053

## 1. Назначение
Единый каталог сущностей Sprint 7B.

## 2. Scope
Покрывает:
- M-051 Workflow Orchestration Backbone
- M-052 Optimization Recommendation Engine
- M-053 Operator Copilot Feed

Опирается на:
- deal
- workflow-relevant sets from prior sprints
- learning_automation_set
- dashboard_snapshot_set
- incident / KPI / finance / risk / execution context
- event_record

## 3. Canonical refs
- workflow_run_set_id => WRS-YYYY-NNNNNN
- workflow_run_id => WR-YYYY-NNNNNN
- workflow_step_id => WS-YYYY-NNNNNN
- optimization_recommendation_set_id => ORS-YYYY-NNNNNN
- optimization_recommendation_id => OR-YYYY-NNNNNN
- copilot_feed_set_id => CFS-YYYY-NNNNNN
- copilot_feed_id => CF-YYYY-NNNNNN

## 4. Инварианты
1. Workflow runs always link to explicit scope.
2. Optimization recommendations must remain traceable to signals/context.
3. Copilot feed is built from persisted workflow/optimization context.
4. Recommendations and feed items are append-only.
5. Human actions remain separate from system suggestions.

# 5. M-051 entities

## workflow_run_set
- id
- workflow_run_set_id
- scope_type
- scope_ref
- workflow_status
- created_at
- updated_at

## workflow_run_record
- id
- workflow_run_id
- workflow_run_set_id
- summary_text
- current_phase
- created_at
- updated_at

## workflow_step_record
- id
- workflow_step_id
- workflow_run_id
- step_code
- step_type
- step_status
- depends_on_step_ref
- source_ref
- created_at
- updated_at

# 6. M-052 entities

## optimization_recommendation_set
- id
- optimization_recommendation_set_id
- scope_type
- scope_ref
- optimization_status
- created_at
- updated_at

## optimization_recommendation_record
- id
- optimization_recommendation_id
- optimization_recommendation_set_id
- recommendation_code
- recommendation_type
- recommendation_text
- confidence_score
- created_at
- updated_at

## optimization_signal_record
- id
- optimization_recommendation_id
- signal_code
- signal_value_text
- source_ref
- created_at

# 7. M-053 entities

## copilot_feed_set
- id
- copilot_feed_set_id
- scope_type
- scope_ref
- feed_status
- created_at
- updated_at

## copilot_feed_record
- id
- copilot_feed_id
- copilot_feed_set_id
- summary_text
- created_at
- updated_at

## copilot_feed_item
- id
- copilot_feed_id
- item_code
- item_type
- priority
- item_text
- source_ref
- created_at

# 8. Enums
WorkflowScopeType:
- DEAL
- PIPELINE
- EXECUTION
- PORTFOLIO

WorkflowStatus:
- BUILT
- ACTIVE
- COMPLETED
- FAILED
- STALE

WorkflowStepType:
- CHECK
- BUILD
- REVIEW
- FOLLOW_UP
- ESCALATE
- CLOSE
- OTHER

WorkflowStepStatus:
- PENDING
- READY
- IN_PROGRESS
- DONE
- BLOCKED
- SKIPPED

OptimizationScopeType:
- DEAL
- PORTFOLIO
- SUPPLIER
- PROCESS

OptimizationStatus:
- BUILT
- FAILED
- STALE

OptimizationRecommendationType:
- CYCLE_TIME
- MARGIN
- RISK_REDUCTION
- SUPPLIER_STRATEGY
- PROCESS_DISCIPLINE
- OTHER

CopilotFeedStatus:
- BUILT
- FAILED
- STALE

CopilotFeedItemType:
- ACTION
- ALERT
- RECOMMENDATION
- REMINDER
- FOLLOW_UP
- OTHER

CopilotPriority:
- LOW
- MEDIUM
- HIGH
- CRITICAL

# 9. DTO contracts

BuildWorkflowRunRequest:
{
  "scope_type": "DEAL",
  "scope_ref": "DL-2026-000001"
}

BuildOptimizationRequest:
{
  "scope_type": "PORTFOLIO",
  "scope_ref": "GLOBAL"
}

BuildCopilotFeedRequest:
{
  "scope_type": "EXECUTION",
  "scope_ref": "ECS-2026-000001"
}

# 10. Event contracts
- workflow_run_built
- workflow_step_recorded
- workflow_run_failed
- optimization_recommendations_built
- optimization_signal_recorded
- optimization_recommendations_failed
- copilot_feed_built
- copilot_feed_item_recorded
- copilot_feed_failed

# 11. Migration order
- 048 workflow orchestration
- 049 optimization recommendations
- 050 copilot feed

# 12. Anti-chaos rules
1. Do not serve orchestration only as transient logic.
2. Do not merge optimization recommendations with copilot feed.
3. Do not overwrite prior recommendations or feed items.
4. Do not collapse system suggestions into human actions.
