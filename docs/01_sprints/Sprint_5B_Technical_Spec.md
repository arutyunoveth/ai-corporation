# Sprint 5B Technical Spec
## Модули M-033, M-035, M-036, M-037

## 1. Назначение
Sprint 5B строит слой submission layer поверх уже готового:
- Sprint 1 foundation
- Sprint 2A intake foundation
- Sprint 2B analysis foundation
- Sprint 3A supplier-side foundation
- Sprint 3B supplier quality layer
- Sprint 4A economics layer
- Sprint 4B risk + approval layer
- Sprint 5A bid-prep foundation

Модули:
- M-033 Submission Control
- M-035 Submission Receipt Registry
- M-036 Post-Submission Tracker
- M-037 Outcome Intake

## 2. Результат Sprint 5B
К концу Sprint 5B система должна уметь:
1. создавать formal submission execution package;
2. фиксировать controlled submission attempts;
3. регистрировать submission receipts and evidence;
4. трекать post-submission events;
5. фиксировать outcome сделки как explicit persisted object;
6. писать event/audit trace по submission layer;
7. замкнуть MVP-коридор первой волны:
   intake → analysis → supplier-side → economics → risk/approval → bid prep → submission → outcome.

Итог:
из submission-ready package получить formal submitted deal package:
submission control + receipt + post-submission tracker + outcome.

## 3. Что не входит
- execution branch after award
- delivery control
- payment collection
- incident handling after delivery
- advanced portal automation / browser robots
- full appeals / dispute workflows

## 4. Зависимости
Использует:
- deal / event log / document store
- submission_readiness_set from Sprint 5A
- bid_package_set from Sprint 5A
- ceo_approval_set from Sprint 4B
- existing artifacts and readiness recommendation

## 5. Архитектурные принципы
1. Submission attempt is a persisted business object.
2. Receipt is distinct from submission attempt.
3. Post-submission tracking is distinct from final outcome.
4. Outcome must be explicit and append-only.
5. Every business-significant step emits events.

# 6. M-033 — Submission Control

## Назначение
Control and persist submission attempts.

## Сущности
- submission_execution_sets
- submission_execution_records
- submission_attempts

## Таблицы
### submission_execution_sets
- id
- submission_execution_set_id (`SES-YYYY-NNNNNN`)
- deal_id
- submission_readiness_set_id
- bid_package_set_id
- execution_status (`READY|IN_PROGRESS|SUBMITTED|FAILED|CANCELLED`)
- created_at
- updated_at

### submission_execution_records
- id
- submission_execution_id (`SE-YYYY-NNNNNN`)
- submission_execution_set_id
- channel_type (`MANUAL|PORTAL|API|OTHER`)
- initiated_by_ref
- started_at
- finished_at
- created_at
- updated_at

### submission_attempts
- id
- submission_attempt_id (`SA-YYYY-NNNNNN`)
- submission_execution_id
- attempt_no
- attempt_status (`STARTED|SUCCEEDED|FAILED|ABORTED`)
- notes
- created_at
- updated_at

## API
- POST /submission-control/build
- POST /submission-control/start
- POST /submission-control/attempts
- GET /submission-control/{submission_execution_set_id}
- GET /submission-control?deal_id=...
- GET /submission-control/records/{submission_execution_id}

## Events
- submission_control_built
- submission_execution_started
- submission_attempt_recorded
- submission_execution_failed
- submission_execution_submitted

## Acceptance criteria
1. Submission execution set built from readiness + package.
2. Submission execution record persisted.
3. Attempts persisted append-only.
4. Queryable by deal.
5. Events written to event log.

# 7. M-035 — Submission Receipt Registry

## Назначение
Persist proof of submission and registry/evidence objects.

## Сущности
- submission_receipt_sets
- submission_receipt_records
- submission_receipt_bindings

## Таблицы
### submission_receipt_sets
- id
- submission_receipt_set_id (`SRSR-YYYY-NNNNNN`)
- deal_id
- submission_execution_set_id
- receipt_status (`REGISTERED|PARTIAL|FAILED`)
- created_at
- updated_at

### submission_receipt_records
- id
- submission_receipt_id (`SRR-YYYY-NNNNNN`)
- submission_receipt_set_id
- receipt_number
- receipt_timestamp
- receipt_source (`PORTAL|EMAIL|MANUAL|OTHER`)
- created_at
- updated_at

### submission_receipt_bindings
- id
- submission_receipt_id
- artifact_ref
- binding_type (`SCREENSHOT|PDF|EMAIL|OTHER`)
- created_at

## API
- POST /submission-receipts/register
- GET /submission-receipts/{submission_receipt_set_id}
- GET /submission-receipts?deal_id=...
- GET /submission-receipts/records/{submission_receipt_id}

## Events
- submission_receipt_registered
- submission_receipt_failed

## Acceptance criteria
1. Receipt set registered from submission execution.
2. Receipt record persisted.
3. Evidence bindings persisted.
4. Queryable by deal.
5. Events written to event log.

# 8. M-036 — Post-Submission Tracker

## Назначение
Track post-submission events before final outcome.

## Сущности
- post_submission_tracker_sets
- post_submission_tracker_records
- post_submission_events

## Таблицы
### post_submission_tracker_sets
- id
- post_submission_tracker_set_id (`PSTS-YYYY-NNNNNN`)
- deal_id
- submission_execution_set_id
- tracker_status (`ACTIVE|CLOSED|STALE`)
- created_at
- updated_at

### post_submission_tracker_records
- id
- post_submission_tracker_id (`PST-YYYY-NNNNNN`)
- post_submission_tracker_set_id
- current_stage (`SUBMITTED|UNDER_REVIEW|CLARIFICATION|AWARDED|LOST|CANCELLED|OTHER`)
- summary_text
- created_at
- updated_at

### post_submission_events
- id
- post_submission_event_id (`PSE-YYYY-NNNNNN`)
- post_submission_tracker_id
- event_type (`STATUS_UPDATE|CLARIFICATION|REQUEST|NOTICE|OTHER`)
- event_timestamp
- summary
- source_ref
- created_at

## API
- POST /post-submission/build
- POST /post-submission/events
- GET /post-submission/{post_submission_tracker_set_id}
- GET /post-submission?deal_id=...
- GET /post-submission/records/{post_submission_tracker_id}

## Events
- post_submission_tracker_built
- post_submission_event_recorded
- post_submission_tracker_closed

## Acceptance criteria
1. Tracker set built after submission.
2. Tracker record persisted.
3. Post-submission events persisted append-only.
4. Queryable by deal.
5. Events written to event log.

# 9. M-037 — Outcome Intake

## Назначение
Persist final explicit outcome of the tender.

## Сущности
- outcome_intake_sets
- outcome_intake_records
- outcome_intake_bindings

## Таблицы
### outcome_intake_sets
- id
- outcome_intake_set_id (`OIS-YYYY-NNNNNN`)
- deal_id
- post_submission_tracker_set_id
- outcome_status (`RECORDED|REVISED|FAILED`)
- created_at
- updated_at

### outcome_intake_records
- id
- outcome_intake_id (`OI-YYYY-NNNNNN`)
- outcome_intake_set_id
- outcome_code (`WON|LOST|REJECTED|CANCELLED|NO_RESULT`)
- effective_at
- rationale
- created_at
- updated_at

### outcome_intake_bindings
- id
- outcome_intake_id
- artifact_ref
- binding_type (`NOTICE|PROTOCOL|EMAIL|OTHER`)
- created_at

## API
- POST /outcome-intake/register
- GET /outcome-intake/{outcome_intake_set_id}
- GET /outcome-intake?deal_id=...
- GET /outcome-intake/records/{outcome_intake_id}

## Events
- outcome_intake_recorded
- outcome_intake_revised
- outcome_intake_failed

## Acceptance criteria
1. Outcome set registered from post-submission tracker.
2. Outcome record persisted.
3. Evidence bindings persisted.
4. Queryable by deal.
5. Events written to event log.

# 10. Общие enums Sprint 5B

## SubmissionExecutionStatus
- READY
- IN_PROGRESS
- SUBMITTED
- FAILED
- CANCELLED

## SubmissionAttemptStatus
- STARTED
- SUCCEEDED
- FAILED
- ABORTED

## SubmissionReceiptStatus
- REGISTERED
- PARTIAL
- FAILED

## ReceiptSourceType
- PORTAL
- EMAIL
- MANUAL
- OTHER

## PostSubmissionTrackerStatus
- ACTIVE
- CLOSED
- STALE

## PostSubmissionStage
- SUBMITTED
- UNDER_REVIEW
- CLARIFICATION
- AWARDED
- LOST
- CANCELLED
- OTHER

## PostSubmissionEventType
- STATUS_UPDATE
- CLARIFICATION
- REQUEST
- NOTICE
- OTHER

## OutcomeStatus
- RECORDED
- REVISED
- FAILED

## OutcomeCode
- WON
- LOST
- REJECTED
- CANCELLED
- NO_RESULT

# 11. Поток Sprint 5B
submission readiness
  -> submission control
  -> submission receipt
  -> post-submission tracker
  -> outcome intake
  -> MVP corridor closed

# 12. Migration order Sprint 5B
- Migration 032: submission control tables
- Migration 033: submission receipt tables
- Migration 034: post-submission tracker tables
- Migration 035: outcome intake tables

# 13. Acceptance criteria по всему Sprint 5B
1. submission control formalized;
2. receipt registry formalized;
3. post-submission tracker formalized;
4. outcome intake formalized;
5. all outputs linked to deal;
6. actual submission separated from readiness recommendation;
7. event trace preserved;
8. MVP first-wave corridor closed.
