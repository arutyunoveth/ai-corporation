# Entity Catalog Sprint 5B
## Модули M-033, M-035, M-036, M-037

## 1. Назначение
Единый каталог сущностей Sprint 5B.

## 2. Scope
Покрывает:
- M-033 Submission Control
- M-035 Submission Receipt Registry
- M-036 Post-Submission Tracker
- M-037 Outcome Intake

Опирается на:
- deal
- submission_readiness_set
- bid_package_set
- ceo_approval_set
- document_artifact
- event_record

## 3. Canonical refs
- submission_execution_set_id => SES-YYYY-NNNNNN
- submission_execution_id => SE-YYYY-NNNNNN
- submission_attempt_id => SA-YYYY-NNNNNN
- submission_receipt_set_id => SRSR-YYYY-NNNNNN
- submission_receipt_id => SRR-YYYY-NNNNNN
- post_submission_tracker_set_id => PSTS-YYYY-NNNNNN
- post_submission_tracker_id => PST-YYYY-NNNNNN
- post_submission_event_id => PSE-YYYY-NNNNNN
- outcome_intake_set_id => OIS-YYYY-NNNNNN
- outcome_intake_id => OI-YYYY-NNNNNN

## 4. Инварианты
1. Submission control always links to deal and readiness/package context.
2. Receipt cannot exist without submission execution context.
3. Post-submission tracker cannot exist without submission execution.
4. Outcome cannot be registered without post-submission context.
5. Submission recommendation and actual submission must remain separate.
6. Outcome is append-only and explicit.

# 5. M-033 entities

## submission_execution_set
- id
- submission_execution_set_id
- deal_id
- submission_readiness_set_id
- bid_package_set_id
- execution_status
- created_at
- updated_at

## submission_execution_record
- id
- submission_execution_id
- submission_execution_set_id
- channel_type
- initiated_by_ref
- started_at
- finished_at
- created_at
- updated_at

## submission_attempt
- id
- submission_attempt_id
- submission_execution_id
- attempt_no
- attempt_status
- notes
- created_at
- updated_at

Enums:
SubmissionExecutionStatus:
- READY
- IN_PROGRESS
- SUBMITTED
- FAILED
- CANCELLED

SubmissionAttemptStatus:
- STARTED
- SUCCEEDED
- FAILED
- ABORTED

# 6. M-035 entities

## submission_receipt_set
- id
- submission_receipt_set_id
- deal_id
- submission_execution_set_id
- receipt_status
- created_at
- updated_at

## submission_receipt_record
- id
- submission_receipt_id
- submission_receipt_set_id
- receipt_number
- receipt_timestamp
- receipt_source
- created_at
- updated_at

## submission_receipt_binding
- id
- submission_receipt_id
- artifact_ref
- binding_type
- created_at

Enums:
SubmissionReceiptStatus:
- REGISTERED
- PARTIAL
- FAILED

ReceiptSourceType:
- PORTAL
- EMAIL
- MANUAL
- OTHER

# 7. M-036 entities

## post_submission_tracker_set
- id
- post_submission_tracker_set_id
- deal_id
- submission_execution_set_id
- tracker_status
- created_at
- updated_at

## post_submission_tracker_record
- id
- post_submission_tracker_id
- post_submission_tracker_set_id
- current_stage
- summary_text
- created_at
- updated_at

## post_submission_event
- id
- post_submission_event_id
- post_submission_tracker_id
- event_type
- event_timestamp
- summary
- source_ref
- created_at

Enums:
PostSubmissionTrackerStatus:
- ACTIVE
- CLOSED
- STALE

PostSubmissionStage:
- SUBMITTED
- UNDER_REVIEW
- CLARIFICATION
- AWARDED
- LOST
- CANCELLED
- OTHER

PostSubmissionEventType:
- STATUS_UPDATE
- CLARIFICATION
- REQUEST
- NOTICE
- OTHER

# 8. M-037 entities

## outcome_intake_set
- id
- outcome_intake_set_id
- deal_id
- post_submission_tracker_set_id
- outcome_status
- created_at
- updated_at

## outcome_intake_record
- id
- outcome_intake_id
- outcome_intake_set_id
- outcome_code
- effective_at
- rationale
- created_at
- updated_at

## outcome_intake_binding
- id
- outcome_intake_id
- artifact_ref
- binding_type
- created_at

Enums:
OutcomeStatus:
- RECORDED
- REVISED
- FAILED

OutcomeCode:
- WON
- LOST
- REJECTED
- CANCELLED
- NO_RESULT

# 9. DTO contracts

BuildSubmissionControlRequest:
{
  "deal_id": "DL-2026-000001",
  "submission_readiness_set_id": "SRS-2026-000001",
  "bid_package_set_id": "BPS-2026-000001"
}

RegisterSubmissionAttemptRequest:
{
  "submission_execution_id": "SE-2026-000001",
  "attempt_no": 1,
  "attempt_status": "STARTED",
  "notes": "Начали ручную подачу на ЭТП"
}

RegisterSubmissionReceiptRequest:
{
  "deal_id": "DL-2026-000001",
  "submission_execution_set_id": "SES-2026-000001",
  "receipt_number": "ETP-123456",
  "receipt_timestamp": "2026-06-03T10:00:00Z",
  "receipt_source": "PORTAL"
}

BuildPostSubmissionTrackerRequest:
{
  "deal_id": "DL-2026-000001",
  "submission_execution_set_id": "SES-2026-000001"
}

RegisterOutcomeIntakeRequest:
{
  "deal_id": "DL-2026-000001",
  "post_submission_tracker_set_id": "PSTS-2026-000001",
  "outcome_code": "WON",
  "effective_at": "2026-06-10T12:00:00Z",
  "rationale": "Победа по итогам рассмотрения"
}

# 10. Event contracts
- submission_control_built
- submission_execution_started
- submission_attempt_recorded
- submission_execution_failed
- submission_execution_submitted
- submission_receipt_registered
- submission_receipt_failed
- post_submission_tracker_built
- post_submission_event_recorded
- post_submission_tracker_closed
- outcome_intake_recorded
- outcome_intake_revised
- outcome_intake_failed

# 11. Migration order
- 032 submission control
- 033 submission receipt
- 034 post-submission tracker
- 035 outcome intake

# 12. Anti-chaos rules
1. Do not treat readiness recommendation as actual submission state.
2. Do not register receipt only as an artifact without header record.
3. Do not merge post-submission tracker with outcome.
4. Do not overwrite prior attempts or outcomes; append new records.
