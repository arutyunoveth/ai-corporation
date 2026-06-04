# Sprint 7B Technical Spec
## Модули M-051, M-052, M-053

## 1. Назначение
Sprint 7B строит optimization / orchestration layer поверх уже готового:
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

Модули:
- M-051 Workflow Orchestration Backbone
- M-052 Optimization Recommendation Engine
- M-053 Operator Copilot Feed

## 2. Результат Sprint 7B
К концу Sprint 7B система должна уметь:
1. строить formal workflow orchestration runs across existing modules;
2. фиксировать next-best-action and dependency-based execution steps;
3. собирать optimization recommendations from completed and active deals;
4. формировать operator-facing copilot feed из actionable cards;
5. писать event/audit trace;
6. подготовить foundation для следующего слоя: external connectors / human interface / semi-autonomous control.

Итог:
из completed loops и active operations получить orchestration package:
workflow runs + optimization recommendations + operator copilot feed.

## 3. Что не входит
- real autonomous agent execution over external systems
- browser/portal robotics
- full UI frontend
- reinforcement learning / automatic policy optimization
- human replacement in regulated sign-off steps

## 4. Зависимости
Использует:
- deal / event log / decision journal / document store
- archive export and learning automation from Sprint 7A
- active execution / submission / bid readiness context from prior sprints
- KPI, incidents, outcomes, finance and risk layers

## 5. Архитектурные принципы
1. Orchestration run is a persisted business object.
2. Optimization recommendations remain explainable and traceable.
3. Operator copilot feed is distinct from workflow orchestration.
4. System recommendations and human actions remain separate.
5. Every business-significant run emits events.

# 6. M-051 — Workflow Orchestration Backbone

## Назначение
Persist orchestrated workflow runs and actionable next steps across the system.

## Сущности
- workflow_run_sets
- workflow_run_records
- workflow_step_records

## Таблицы
### workflow_run_sets
- id
- workflow_run_set_id (`WRS-YYYY-NNNNNN`)
- scope_type (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- scope_ref
- workflow_status (`BUILT|ACTIVE|COMPLETED|FAILED|STALE`)
- created_at
- updated_at

### workflow_run_records
- id
- workflow_run_id (`WR-YYYY-NNNNNN`)
- workflow_run_set_id
- summary_text
- current_phase
- created_at
- updated_at

### workflow_step_records
- id
- workflow_step_id (`WS-YYYY-NNNNNN`)
- workflow_run_id
- step_code
- step_type (`CHECK|BUILD|REVIEW|FOLLOW_UP|ESCALATE|CLOSE|OTHER`)
- step_status (`PENDING|READY|IN_PROGRESS|DONE|BLOCKED|SKIPPED`)
- depends_on_step_ref
- source_ref
- created_at
- updated_at

## API
- POST /workflow-runs/build
- GET /workflow-runs/{workflow_run_set_id}
- GET /workflow-runs?scope_type=...&scope_ref=...
- GET /workflow-runs/records/{workflow_run_id}

## Events
- workflow_run_built
- workflow_step_recorded
- workflow_run_failed

# 7. M-052 — Optimization Recommendation Engine

## Назначение
Generate reusable optimization recommendations from operational history and live context.

## Сущности
- optimization_recommendation_sets
- optimization_recommendation_records
- optimization_signal_records

## Таблицы
### optimization_recommendation_sets
- id
- optimization_recommendation_set_id (`ORS-YYYY-NNNNNN`)
- scope_type (`DEAL|PORTFOLIO|SUPPLIER|PROCESS`)
- scope_ref
- optimization_status (`BUILT|FAILED|STALE`)
- created_at
- updated_at

### optimization_recommendation_records
- id
- optimization_recommendation_id (`OR-YYYY-NNNNNN`)
- optimization_recommendation_set_id
- recommendation_code
- recommendation_type (`CYCLE_TIME|MARGIN|RISK_REDUCTION|SUPPLIER_STRATEGY|PROCESS_DISCIPLINE|OTHER`)
- recommendation_text
- confidence_score
- created_at
- updated_at

### optimization_signal_records
- id
- optimization_recommendation_id
- signal_code
- signal_value_text
- source_ref
- created_at

## API
- POST /optimization/build
- GET /optimization/{optimization_recommendation_set_id}
- GET /optimization?scope_type=...&scope_ref=...
- GET /optimization/records/{optimization_recommendation_id}

## Events
- optimization_recommendations_built
- optimization_signal_recorded
- optimization_recommendations_failed

# 8. M-053 — Operator Copilot Feed

## Назначение
Build operator-facing feed of actionable cards from workflow and optimization context.

## Сущности
- copilot_feed_sets
- copilot_feed_records
- copilot_feed_items

## Таблицы
### copilot_feed_sets
- id
- copilot_feed_set_id (`CFS-YYYY-NNNNNN`)
- scope_type (`DEAL|PIPELINE|EXECUTION|PORTFOLIO`)
- scope_ref
- feed_status (`BUILT|FAILED|STALE`)
- created_at
- updated_at

### copilot_feed_records
- id
- copilot_feed_id (`CF-YYYY-NNNNNN`)
- copilot_feed_set_id
- summary_text
- created_at
- updated_at

### copilot_feed_items
- id
- copilot_feed_id
- item_code
- item_type (`ACTION|ALERT|RECOMMENDATION|REMINDER|FOLLOW_UP|OTHER`)
- priority (`LOW|MEDIUM|HIGH|CRITICAL`)
- item_text
- source_ref
- created_at

## API
- POST /copilot-feed/build
- GET /copilot-feed/{copilot_feed_set_id}
- GET /copilot-feed?scope_type=...&scope_ref=...
- GET /copilot-feed/records/{copilot_feed_id}

## Events
- copilot_feed_built
- copilot_feed_item_recorded
- copilot_feed_failed

# 9. Общие enums Sprint 7B
- WorkflowScopeType = DEAL, PIPELINE, EXECUTION, PORTFOLIO
- WorkflowStatus = BUILT, ACTIVE, COMPLETED, FAILED, STALE
- WorkflowStepType = CHECK, BUILD, REVIEW, FOLLOW_UP, ESCALATE, CLOSE, OTHER
- WorkflowStepStatus = PENDING, READY, IN_PROGRESS, DONE, BLOCKED, SKIPPED
- OptimizationScopeType = DEAL, PORTFOLIO, SUPPLIER, PROCESS
- OptimizationStatus = BUILT, FAILED, STALE
- OptimizationRecommendationType = CYCLE_TIME, MARGIN, RISK_REDUCTION, SUPPLIER_STRATEGY, PROCESS_DISCIPLINE, OTHER
- CopilotFeedStatus = BUILT, FAILED, STALE
- CopilotFeedItemType = ACTION, ALERT, RECOMMENDATION, REMINDER, FOLLOW_UP, OTHER
- CopilotPriority = LOW, MEDIUM, HIGH, CRITICAL

# 10. Поток Sprint 7B
active and closed deal context
  -> workflow orchestration runs
  -> optimization recommendations
  -> operator copilot feed
  -> ready for connectors / UX / semi-autonomous control

# 11. Migration order Sprint 7B
- Migration 048: workflow orchestration tables
- Migration 049: optimization recommendation tables
- Migration 050: copilot feed tables

# 12. Acceptance criteria по всему Sprint 7B
1. workflow orchestration formalized;
2. optimization recommendations formalized;
3. copilot feed formalized;
4. all outputs queryable and linked to scope/deal;
5. event trace preserved;
6. foundation ready for connectors / UX / semi-autonomous control.
