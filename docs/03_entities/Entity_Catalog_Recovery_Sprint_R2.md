# Entity Catalog Recovery Sprint R2
## Канонические модули M-031, M-032, M-033, M-034

## 1. Назначение
Единый каталог сущностей для controlled recovery step R2.

## 2. M-031 Bid Completeness Checker

### Canonical refs
- bid_completeness_set_id => BCS-YYYY-NNNNNN
- bid_completeness_id => BC-YYYY-NNNNNN
- bid_readiness_report_id => BRR-YYYY-NNNNNN

### Таблицы
#### bid_completeness_sets
- id
- bid_completeness_set_id
- deal_id
- completeness_status
- created_at
- updated_at

#### bid_completeness_records
- id
- bid_completeness_id
- bid_completeness_set_id
- mandatory_total
- mandatory_present
- optional_present
- summary_text
- created_at
- updated_at

#### bid_completeness_flags
- id
- bid_completeness_id
- flag_code
- severity
- summary
- source_ref
- created_at

#### bid_readiness_reports
- id
- bid_readiness_report_id
- bid_completeness_set_id
- readiness_summary
- blocking_issue_count
- created_at
- updated_at

## 3. M-032 Submission Archive

### Canonical refs
- submission_archive_set_id => SAS-YYYY-NNNNNN
- submission_archive_id => SAR-YYYY-NNNNNN

### Таблицы
#### submission_archive_sets
- id
- submission_archive_set_id
- deal_id
- archive_status
- created_at
- updated_at

#### submission_archive_records
- id
- submission_archive_id
- submission_archive_set_id
- archive_manifest_json
- proof_summary
- created_at
- updated_at

#### submission_archive_items
- id
- submission_archive_id
- artifact_ref
- item_role
- created_at

## 4. M-033 Tender Procedure Monitor

### Canonical refs
- procedure_monitor_set_id => PMS-YYYY-NNNNNN
- procedure_monitor_id => PM-YYYY-NNNNNN
- procedure_event_id => PME-YYYY-NNNNNN

### Таблицы
#### procedure_monitor_sets
- id
- procedure_monitor_set_id
- deal_id
- procedure_status
- created_at
- updated_at

#### procedure_monitor_records
- id
- procedure_monitor_id
- procedure_monitor_set_id
- current_stage
- summary_text
- created_at
- updated_at

#### procedure_monitor_events
- id
- procedure_event_id
- procedure_monitor_id
- event_type
- event_timestamp
- summary
- source_ref
- created_at

#### procedure_monitor_alerts
- id
- procedure_monitor_id
- alert_code
- severity
- summary
- created_at

## 5. M-034 Contract Negotiation Workspace

### Canonical refs
- contract_negotiation_set_id => CNS-YYYY-NNNNNN
- contract_negotiation_id => CN-YYYY-NNNNNN

### Таблицы
#### contract_negotiation_sets
- id
- contract_negotiation_set_id
- deal_id
- negotiation_status
- created_at
- updated_at

#### contract_negotiation_records
- id
- contract_negotiation_id
- contract_negotiation_set_id
- summary_text
- negotiation_pack_manifest_json
- created_at
- updated_at

#### contract_negotiation_issues
- id
- contract_negotiation_id
- issue_code
- issue_text
- severity
- created_at

#### contract_negotiation_comments
- id
- contract_negotiation_id
- clause_ref
- comment_text
- created_at

## 6. DTO contracts
### CheckBidCompletenessRequest
{
  "deal_id": "DL-2026-000001",
  "bid_package_set_id": "BPS-2026-000001"
}

### BuildSubmissionArchiveRequest
{
  "deal_id": "DL-2026-000001",
  "bid_package_set_id": "BPS-2026-000001"
}

### BuildProcedureMonitorRequest
{
  "deal_id": "DL-2026-000001"
}

### BuildContractNegotiationRequest
{
  "deal_id": "DL-2026-000001"
}

## 7. Anti-chaos rules
1. M-032 Submission Archive must remain separate from readiness/control helpers.
2. M-033 Tender Procedure Monitor must remain separate from current internal tracker/outcome helpers.
3. M-034 must be canonical workspace for contracting, not a generic helper.
4. No new canonical IDs beyond master-registry.
