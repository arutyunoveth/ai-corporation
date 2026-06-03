# Sprint 7A Technical Spec
## Модули M-048, M-049, M-050

## 1. Назначение
Sprint 7A строит слой operational intelligence / archive export / learning automation поверх уже готового:
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

Модули:
- M-048 Operational Dashboard Backbone
- M-049 Archive Export & Handover
- M-050 Learning Automation Engine

## 2. Результат Sprint 7A
К концу Sprint 7A система должна уметь:
1. строить persisted operational dashboard snapshots;
2. собирать portfolio-level and deal-level summary views;
3. экспортировать archive/handover package по закрытой сделке;
4. создавать formal archive export manifests and artifacts;
5. агрегировать learning outputs from completed deals;
6. строить reusable recommendations / playbook suggestions for future deals;
7. писать event/audit trace;
8. подготовить foundation для следующего контура: optimization / orchestration / assistants UX.

Итог:
из closure package получить operational intelligence package:
dashboard snapshot + archive export + automated learning outputs.

## 3. Что не входит
- real-time frontend dashboard UI
- external BI warehouse
- autonomous strategy optimizer
- self-modifying prompts/code
- cross-project workforce planning
- full knowledge graph infrastructure

## 4. Зависимости
Использует:
- deal / event log / document store
- deal closure / archive snapshot from Sprint 6B
- KPI & learning loop from Sprint 6B
- outcome / execution / finance / risk context from prior sprints

## 5. Архитектурные принципы
1. Dashboard data must be persisted snapshots, not only transient queries.
2. Archive export is distinct from archive snapshot.
3. Learning automation is distinct from raw KPI notes.
4. Recommendations must remain explainable and traceable to completed deals.
5. Every business-significant run emits events.

# 6. M-048 — Operational Dashboard Backbone

## Назначение
Persist operational dashboard snapshots and rollups for monitoring.

## Сущности
- dashboard_snapshot_sets
- dashboard_snapshot_records
- dashboard_metric_records

## Таблицы
### dashboard_snapshot_sets
- id
- dashboard_snapshot_set_id (`DSS-YYYY-NNNNNN`)
- scope_type (`GLOBAL|DEAL|PIPELINE|EXECUTION`)
- scope_ref
- snapshot_status (`BUILT|FAILED|STALE`)
- created_at
- updated_at

### dashboard_snapshot_records
- id
- dashboard_snapshot_id (`DSH-YYYY-NNNNNN`)
- dashboard_snapshot_set_id
- summary_text
- created_at
- updated_at

### dashboard_metric_records
- id
- dashboard_snapshot_id
- metric_code
- metric_value_numeric
- metric_value_text
- created_at

## API
- POST /dashboards/build
- GET /dashboards/{dashboard_snapshot_set_id}
- GET /dashboards?scope_type=...&scope_ref=...
- GET /dashboards/records/{dashboard_snapshot_id}

## Events
- dashboard_snapshot_built
- dashboard_snapshot_failed

# 7. M-049 — Archive Export & Handover

## Назначение
Create portable archive export package from closed deal context.

## Сущности
- archive_export_sets
- archive_export_records
- archive_export_items

## Таблицы
### archive_export_sets
- id
- archive_export_set_id (`AES-YYYY-NNNNNN`)
- deal_id
- deal_closure_set_id
- export_status (`BUILT|FAILED|STALE|EXPORTED`)
- created_at
- updated_at

### archive_export_records
- id
- archive_export_id (`AE-YYYY-NNNNNN`)
- archive_export_set_id
- export_manifest_json
- export_format (`MANIFEST|ZIP_MANIFEST|JSON_BUNDLE|OTHER`)
- created_at
- updated_at

### archive_export_items
- id
- archive_export_id
- artifact_ref
- item_role (`CORE_DOC|EVIDENCE|DECISION|FINANCE|EXECUTION|OTHER`)
- created_at

## API
- POST /archive-export/build
- GET /archive-export/{archive_export_set_id}
- GET /archive-export?deal_id=...
- GET /archive-export/records/{archive_export_id}

## Events
- archive_export_built
- archive_export_failed
- archive_export_marked_exported

# 8. M-050 — Learning Automation Engine

## Назначение
Aggregate KPI and learning notes into reusable recommendations.

## Сущности
- learning_automation_sets
- learning_automation_records
- learning_recommendation_records

## Таблицы
### learning_automation_sets
- id
- learning_automation_set_id (`LAS-YYYY-NNNNNN`)
- scope_type (`DEAL|PORTFOLIO`)
- scope_ref
- automation_status (`BUILT|FAILED|STALE`)
- created_at
- updated_at

### learning_automation_records
- id
- learning_automation_id (`LA-YYYY-NNNNNN`)
- learning_automation_set_id
- summary_text
- created_at
- updated_at

### learning_recommendation_records
- id
- learning_automation_id
- recommendation_code
- recommendation_type (`PLAYBOOK|CHECKLIST|RISK_PREVENTION|SUPPLIER_STRATEGY|PRICING_DISCIPLINE|OTHER`)
- recommendation_text
- source_ref
- created_at

## API
- POST /learning-automation/build
- GET /learning-automation/{learning_automation_set_id}
- GET /learning-automation?scope_type=...&scope_ref=...
- GET /learning-automation/records/{learning_automation_id}

## Events
- learning_automation_built
- learning_recommendation_recorded
- learning_automation_failed

# 9. Общие enums Sprint 7A
- DashboardScopeType = GLOBAL, DEAL, PIPELINE, EXECUTION
- DashboardSnapshotStatus = BUILT, FAILED, STALE
- ArchiveExportStatus = BUILT, FAILED, STALE, EXPORTED
- ArchiveExportFormat = MANIFEST, ZIP_MANIFEST, JSON_BUNDLE, OTHER
- ArchiveExportItemRole = CORE_DOC, EVIDENCE, DECISION, FINANCE, EXECUTION, OTHER
- LearningAutomationScopeType = DEAL, PORTFOLIO
- LearningAutomationStatus = BUILT, FAILED, STALE
- LearningRecommendationType = PLAYBOOK, CHECKLIST, RISK_PREVENTION, SUPPLIER_STRATEGY, PRICING_DISCIPLINE, OTHER

# 10. Поток Sprint 7A
closed deals + archive + KPI/learning
  -> dashboard snapshots
  -> archive export package
  -> learning automation
  -> ready for next optimization/orchestration layer

# 11. Migration order Sprint 7A
- Migration 045: dashboard snapshot tables
- Migration 046: archive export tables
- Migration 047: learning automation tables

# 12. Acceptance criteria по всему Sprint 7A
1. dashboard snapshots formalized;
2. archive export formalized;
3. learning automation formalized;
4. all outputs queryable and linked to scope/deal;
5. event trace preserved;
6. foundation ready for next optimization/orchestration phase.
