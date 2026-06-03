# Entity Catalog Sprint 6B
## Модули M-045, M-046, M-047

## 1. Назначение
Единый каталог сущностей Sprint 6B.

## 2. Scope
Покрывает:
- M-045 Incident & Escalation Desk
- M-046 Deal Closure & Archive
- M-047 KPI & Learning Loop

Опирается на:
- deal
- outcome_intake_set
- execution_command_set
- incident_set
- finance memo / integrated risk memo where useful
- event_record

## 3. Canonical refs
- incident_set_id => INS-YYYY-NNNNNN
- incident_id => INC-YYYY-NNNNNN
- escalation_id => ESC-YYYY-NNNNNN
- deal_closure_set_id => DCS-YYYY-NNNNNN
- deal_closure_id => DC-YYYY-NNNNNN
- archive_snapshot_id => DAS-YYYY-NNNNNN
- kpi_learning_set_id => KLS-YYYY-NNNNNN
- kpi_learning_id => KLR-YYYY-NNNNNN
- learning_note_id => LN-YYYY-NNNNNN

## 4. Инварианты
1. Incidents always link to deal and execution context.
2. Closure requires explicit outcome context.
3. Archive snapshot is created from closure context, not ad hoc.
4. KPI/learning requires closure context.
5. New incidents, closures and learning notes are append-only.

# 5. M-045 entities

## incident_set
- id
- incident_set_id
- deal_id
- execution_command_set_id
- incident_status
- created_at
- updated_at

## incident_record
- id
- incident_id
- incident_set_id
- incident_type
- severity
- summary
- source_ref
- created_at
- updated_at

## escalation_record
- id
- escalation_id
- incident_id
- escalation_level
- escalation_status
- notes
- created_at
- updated_at

# 6. M-046 entities

## deal_closure_set
- id
- deal_closure_set_id
- deal_id
- outcome_intake_set_id
- execution_command_set_id
- closure_status
- created_at
- updated_at

## deal_closure_record
- id
- deal_closure_id
- deal_closure_set_id
- closure_code
- summary_text
- closed_at
- created_at
- updated_at

## deal_archive_snapshot
- id
- archive_snapshot_id
- deal_closure_set_id
- snapshot_manifest_json
- created_at

# 7. M-047 entities

## kpi_learning_set
- id
- kpi_learning_set_id
- deal_id
- deal_closure_set_id
- kpi_status
- created_at
- updated_at

## kpi_learning_record
- id
- kpi_learning_id
- kpi_learning_set_id
- cycle_time_days
- margin_estimate
- supplier_count
- incident_count
- payment_collection_days
- created_at
- updated_at

## learning_note_record
- id
- learning_note_id
- kpi_learning_id
- note_type
- note_text
- created_at

# 8. Enums
IncidentStatus:
- OPEN
- CONTAINED
- RESOLVED
- STALE

IncidentType:
- DELIVERY
- QUALITY
- PAYMENT
- DOCUMENT
- COMMUNICATION
- OTHER

EscalationLevel:
- OWNER
- SUPPLIER
- CUSTOMER
- LEGAL
- FINANCE
- OTHER

EscalationStatus:
- OPEN
- RESOLVED
- DROPPED

DealClosureStatus:
- READY
- CLOSED
- FAILED
- STALE

DealClosureCode:
- CLOSED_WON
- CLOSED_LOST
- CLOSED_CANCELLED
- CLOSED_NO_RESULT

KPIStatus:
- BUILT
- FAILED
- STALE

LearningNoteType:
- WHAT_WORKED
- WHAT_FAILED
- PROCESS_GAP
- SUPPLIER_LEARNING
- CUSTOMER_LEARNING
- OTHER

# 9. DTO contracts

BuildIncidentSetRequest:
{
  "deal_id": "DL-2026-000001",
  "execution_command_set_id": "ECS-2026-000001"
}

RegisterIncidentRequest:
{
  "incident_set_id": "INS-2026-000001",
  "incident_type": "DELIVERY",
  "severity": "HIGH",
  "summary": "Просрочка от поставщика",
  "source_ref": "SFE-2026-000001"
}

BuildDealClosureRequest:
{
  "deal_id": "DL-2026-000001",
  "outcome_intake_set_id": "OIS-2026-000001",
  "execution_command_set_id": "ECS-2026-000001"
}

BuildKPILearningRequest:
{
  "deal_id": "DL-2026-000001",
  "deal_closure_set_id": "DCS-2026-000001"
}

# 10. Event contracts
- incident_set_built
- incident_recorded
- incident_escalated
- incident_resolved
- deal_closure_built
- deal_closed
- deal_archive_snapshot_created
- deal_closure_failed
- kpi_learning_built
- learning_note_recorded
- kpi_learning_failed

# 11. Migration order
- 042 incidents
- 043 closure / archive
- 044 KPI / learning

# 12. Anti-chaos rules
1. Do not log incidents only inside generic events.
2. Do not close deal without explicit outcome context.
3. Do not treat archive snapshot as a destructive delete.
4. Do not merge KPI snapshot and learning notes into one blob.
