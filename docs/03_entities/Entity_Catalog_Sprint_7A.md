# Entity Catalog Sprint 7A
## Модули M-048, M-049, M-050

## 1. Назначение
Единый каталог сущностей Sprint 7A.

## 2. Scope
Покрывает:
- M-048 Operational Dashboard Backbone
- M-049 Archive Export & Handover
- M-050 Learning Automation Engine

Опирается на:
- deal
- deal_closure_set
- archive_snapshot
- kpi_learning_set
- learning_note_record
- event_record

## 3. Canonical refs
- dashboard_snapshot_set_id => DSS-YYYY-NNNNNN
- dashboard_snapshot_id => DSH-YYYY-NNNNNN
- archive_export_set_id => AES-YYYY-NNNNNN
- archive_export_id => AE-YYYY-NNNNNN
- learning_automation_set_id => LAS-YYYY-NNNNNN
- learning_automation_id => LA-YYYY-NNNNNN

## 4. Инварианты
1. Dashboard snapshots always link to explicit scope.
2. Archive export requires closure context.
3. Learning automation requires KPI/learning context.
4. Export package is distinct from archive snapshot.
5. Learning recommendations are append-only and traceable.

# 5. M-048 entities
## dashboard_snapshot_set
- id
- dashboard_snapshot_set_id
- scope_type
- scope_ref
- snapshot_status
- created_at
- updated_at

## dashboard_snapshot_record
- id
- dashboard_snapshot_id
- dashboard_snapshot_set_id
- summary_text
- created_at
- updated_at

## dashboard_metric_record
- id
- dashboard_snapshot_id
- metric_code
- metric_value_numeric
- metric_value_text
- created_at

# 6. M-049 entities
## archive_export_set
- id
- archive_export_set_id
- deal_id
- deal_closure_set_id
- export_status
- created_at
- updated_at

## archive_export_record
- id
- archive_export_id
- archive_export_set_id
- export_manifest_json
- export_format
- created_at
- updated_at

## archive_export_item
- id
- archive_export_id
- artifact_ref
- item_role
- created_at

# 7. M-050 entities
## learning_automation_set
- id
- learning_automation_set_id
- scope_type
- scope_ref
- automation_status
- created_at
- updated_at

## learning_automation_record
- id
- learning_automation_id
- learning_automation_set_id
- summary_text
- created_at
- updated_at

## learning_recommendation_record
- id
- learning_automation_id
- recommendation_code
- recommendation_type
- recommendation_text
- source_ref
- created_at

# 8. Enums
DashboardScopeType:
- GLOBAL
- DEAL
- PIPELINE
- EXECUTION

DashboardSnapshotStatus:
- BUILT
- FAILED
- STALE

ArchiveExportStatus:
- BUILT
- FAILED
- STALE
- EXPORTED

ArchiveExportFormat:
- MANIFEST
- ZIP_MANIFEST
- JSON_BUNDLE
- OTHER

ArchiveExportItemRole:
- CORE_DOC
- EVIDENCE
- DECISION
- FINANCE
- EXECUTION
- OTHER

LearningAutomationScopeType:
- DEAL
- PORTFOLIO

LearningAutomationStatus:
- BUILT
- FAILED
- STALE

LearningRecommendationType:
- PLAYBOOK
- CHECKLIST
- RISK_PREVENTION
- SUPPLIER_STRATEGY
- PRICING_DISCIPLINE
- OTHER

# 9. DTO contracts
BuildDashboardSnapshotRequest:
{
  "scope_type": "DEAL",
  "scope_ref": "DL-2026-000001"
}

BuildArchiveExportRequest:
{
  "deal_id": "DL-2026-000001",
  "deal_closure_set_id": "DCS-2026-000001"
}

BuildLearningAutomationRequest:
{
  "scope_type": "DEAL",
  "scope_ref": "DL-2026-000001",
  "deal_closure_set_id": "DCS-2026-000001",
  "kpi_learning_set_id": "KLS-2026-000001"
}

# 10. Event contracts
- dashboard_snapshot_built
- dashboard_snapshot_failed
- archive_export_built
- archive_export_failed
- archive_export_marked_exported
- learning_automation_built
- learning_recommendation_recorded
- learning_automation_failed

# 11. Migration order
- 045 dashboard snapshots
- 046 archive export
- 047 learning automation

# 12. Anti-chaos rules
1. Do not serve dashboards only as transient aggregations.
2. Do not treat archive export as the same object as archive snapshot.
3. Do not merge KPI snapshot and learning automation into one object.
4. Do not overwrite prior recommendations; append new records.
