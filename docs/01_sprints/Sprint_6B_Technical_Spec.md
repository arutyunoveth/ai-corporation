# Sprint 6B Technical Spec
## Модули M-045, M-046, M-047

## 1. Назначение
Sprint 6B строит closure / incident / learning contour поверх уже готового:
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

Модули:
- M-045 Incident & Escalation Desk
- M-046 Deal Closure & Archive
- M-047 KPI & Learning Loop

## 2. Результат Sprint 6B
К концу Sprint 6B система должна уметь:
1. регистрировать execution-time incidents and escalations;
2. хранить incident records как formal persisted objects;
3. формально закрывать сделку после outcome/execution completion;
4. архивировать deal context без потери audit trail;
5. собирать KPI snapshot and learning notes;
6. замыкать learning loop для будущих тендеров;
7. писать event/audit trace;
8. завершить первую полную операционную дугу системы.

Итог:
из execution package получить formal closure package:
incidents + closure/archive + KPI snapshot + learning outputs.

## 3. Что не входит
- advanced BI dashboards
- ML retraining pipelines
- external analytics warehouse
- full incident SLA engine
- cross-deal portfolio optimization

## 4. Зависимости
Использует:
- deal / event log / document store
- outcome intake from Sprint 5B
- execution command / milestones / fulfillment / shipping / payment from Sprint 6A
- finance memo / integrated risk memo / approval where useful

## 5. Архитектурные принципы
1. Incident records are persisted business objects.
2. Deal closure is distinct from archive snapshot.
3. KPI snapshot is distinct from learning notes.
4. Closure must not destroy historical traces.
5. Every business-significant step emits events.

# 6. M-045 — Incident & Escalation Desk

## Назначение
Track incidents and escalations during execution / collection / closure.

## Сущности
- incident_sets
- incident_records
- escalation_records

## Таблицы
### incident_sets
- id
- incident_set_id (`INS-YYYY-NNNNNN`)
- deal_id
- execution_command_set_id
- incident_status (`OPEN|CONTAINED|RESOLVED|STALE`)
- created_at
- updated_at

### incident_records
- id
- incident_id (`INC-YYYY-NNNNNN`)
- incident_set_id
- incident_type (`DELIVERY|QUALITY|PAYMENT|DOCUMENT|COMMUNICATION|OTHER`)
- severity (`LOW|MEDIUM|HIGH|CRITICAL`)
- summary
- source_ref
- created_at
- updated_at

### escalation_records
- id
- escalation_id (`ESC-YYYY-NNNNNN`)
- incident_id
- escalation_level (`OWNER|SUPPLIER|CUSTOMER|LEGAL|FINANCE|OTHER`)
- escalation_status (`OPEN|RESOLVED|DROPPED`)
- notes
- created_at
- updated_at

## API
- POST /incidents/build
- POST /incidents/register
- POST /incidents/escalate
- GET /incidents/{incident_set_id}
- GET /incidents?deal_id=...
- GET /incidents/records/{incident_id}

## Events
- incident_set_built
- incident_recorded
- incident_escalated
- incident_resolved

## Acceptance criteria
1. Incident set built from execution context.
2. Incident records persisted.
3. Escalations persisted.
4. Queryable by deal.
5. Events written to event log.

# 7. M-046 — Deal Closure & Archive

## Назначение
Formally close the deal and persist closure/archive context.

## Сущности
- deal_closure_sets
- deal_closure_records
- deal_archive_snapshots

## Таблицы
### deal_closure_sets
- id
- deal_closure_set_id (`DCS-YYYY-NNNNNN`)
- deal_id
- outcome_intake_set_id
- execution_command_set_id
- closure_status (`READY|CLOSED|FAILED|STALE`)
- created_at
- updated_at

### deal_closure_records
- id
- deal_closure_id (`DC-YYYY-NNNNNN`)
- deal_closure_set_id
- closure_code (`CLOSED_WON|CLOSED_LOST|CLOSED_CANCELLED|CLOSED_NO_RESULT`)
- summary_text
- closed_at
- created_at
- updated_at

### deal_archive_snapshots
- id
- archive_snapshot_id (`DAS-YYYY-NNNNNN`)
- deal_closure_set_id
- snapshot_manifest_json
- created_at

## API
- POST /deal-closure/build
- POST /deal-closure/close
- GET /deal-closure/{deal_closure_set_id}
- GET /deal-closure?deal_id=...
- GET /deal-closure/records/{deal_closure_id}

## Events
- deal_closure_built
- deal_closed
- deal_archive_snapshot_created
- deal_closure_failed

## Acceptance criteria
1. Closure package built from outcome + execution context.
2. Closure record persisted.
3. Archive snapshot persisted.
4. Queryable by deal.
5. Events written to event log.

# 8. M-047 — KPI & Learning Loop

## Назначение
Persist KPI snapshot and learning notes from completed deal.

## Сущности
- kpi_learning_sets
- kpi_learning_records
- learning_note_records

## Таблицы
### kpi_learning_sets
- id
- kpi_learning_set_id (`KLS-YYYY-NNNNNN`)
- deal_id
- deal_closure_set_id
- kpi_status (`BUILT|FAILED|STALE`)
- created_at
- updated_at

### kpi_learning_records
- id
- kpi_learning_id (`KLR-YYYY-NNNNNN`)
- kpi_learning_set_id
- cycle_time_days
- margin_estimate
- supplier_count
- incident_count
- payment_collection_days
- created_at
- updated_at

### learning_note_records
- id
- learning_note_id (`LN-YYYY-NNNNNN`)
- kpi_learning_id
- note_type (`WHAT_WORKED|WHAT_FAILED|PROCESS_GAP|SUPPLIER_LEARNING|CUSTOMER_LEARNING|OTHER`)
- note_text
- created_at

## API
- POST /kpi-learning/build
- GET /kpi-learning/{kpi_learning_set_id}
- GET /kpi-learning?deal_id=...
- GET /kpi-learning/records/{kpi_learning_id}

## Events
- kpi_learning_built
- learning_note_recorded
- kpi_learning_failed

## Acceptance criteria
1. KPI set built from closure context.
2. KPI record persisted.
3. Learning notes persisted.
4. Queryable by deal.
5. Events written to event log.

# 9. Общие enums Sprint 6B

## IncidentStatus
- OPEN
- CONTAINED
- RESOLVED
- STALE

## IncidentType
- DELIVERY
- QUALITY
- PAYMENT
- DOCUMENT
- COMMUNICATION
- OTHER

## EscalationLevel
- OWNER
- SUPPLIER
- CUSTOMER
- LEGAL
- FINANCE
- OTHER

## EscalationStatus
- OPEN
- RESOLVED
- DROPPED

## DealClosureStatus
- READY
- CLOSED
- FAILED
- STALE

## DealClosureCode
- CLOSED_WON
- CLOSED_LOST
- CLOSED_CANCELLED
- CLOSED_NO_RESULT

## KPIStatus
- BUILT
- FAILED
- STALE

## LearningNoteType
- WHAT_WORKED
- WHAT_FAILED
- PROCESS_GAP
- SUPPLIER_LEARNING
- CUSTOMER_LEARNING
- OTHER

# 10. Поток Sprint 6B
execution events
  -> incidents / escalations
outcome + execution
  -> closure + archive
closure
  -> KPI snapshot + learning notes
  -> operational loop closed

# 11. Migration order Sprint 6B
- Migration 042: incident / escalation tables
- Migration 043: deal closure / archive tables
- Migration 044: KPI / learning tables

# 12. Acceptance criteria по всему Sprint 6B
1. incidents formalized;
2. closure formalized;
3. archive snapshot formalized;
4. KPI snapshot formalized;
5. learning notes formalized;
6. all outputs linked to deal;
7. event trace preserved;
8. first operational loop closed.
