# Entity Catalog Recovery Sprint R4
## Канонические модули M-039, M-040, M-041, M-042, M-043, M-044

## 1. Назначение
Единый каталог сущностей для controlled recovery step R4.

## 2. M-039 Logistics Tracker

### Canonical refs
- logistics_tracking_set_id => LTS-YYYY-NNNNNN
- logistics_tracking_id => LT-YYYY-NNNNNN
- logistics_tracking_event_id => LTE-YYYY-NNNNNN

### Таблицы
#### logistics_tracking_sets
- id
- logistics_tracking_set_id
- deal_id
- logistics_status
- created_at
- updated_at

#### logistics_tracking_records
- id
- logistics_tracking_id
- logistics_tracking_set_id
- eta_at
- summary_text
- created_at
- updated_at

#### logistics_tracking_events
- id
- logistics_tracking_event_id
- logistics_tracking_id
- event_type
- event_timestamp
- summary
- source_ref
- created_at

#### logistics_tracking_links
- id
- logistics_tracking_id
- source_ref
- created_at

## 3. M-040 Incident Register

### Canonical refs
- incident_register_set_id => IRS-YYYY-NNNNNN
- incident_register_id => IR-YYYY-NNNNNN
- incident_register_event_id => IRE-YYYY-NNNNNN

### Таблицы
#### incident_register_sets
- id
- incident_register_set_id
- deal_id
- incident_status
- created_at
- updated_at

#### incident_register_records
- id
- incident_register_id
- incident_register_set_id
- incident_type
- severity
- summary_text
- created_at
- updated_at

#### incident_register_events
- id
- incident_register_event_id
- incident_register_id
- event_type
- event_timestamp
- summary
- source_ref
- created_at

#### incident_register_flags
- id
- incident_register_id
- flag_code
- severity
- summary
- created_at

## 4. M-041 Acceptance Control

### Canonical refs
- acceptance_control_set_id => ACS-YYYY-NNNNNN
- acceptance_control_id => ACC-YYYY-NNNNNN

### Таблицы
#### acceptance_control_sets
- id
- acceptance_control_set_id
- deal_id
- acceptance_status
- created_at
- updated_at

#### acceptance_control_records
- id
- acceptance_control_id
- acceptance_control_set_id
- summary_text
- resolution_state
- created_at
- updated_at

#### acceptance_remarks
- id
- acceptance_control_id
- remark_code
- remark_text
- severity
- created_at

#### acceptance_resolution_items
- id
- acceptance_control_id
- item_code
- resolution_text
- created_at

## 5. M-042 Closing Docs Pack Builder

### Canonical refs
- closing_docs_set_id => CDS-YYYY-NNNNNN
- closing_docs_id => CD-YYYY-NNNNNN

### Таблицы
#### closing_docs_sets
- id
- closing_docs_set_id
- deal_id
- docs_status
- created_at
- updated_at

#### closing_docs_records
- id
- closing_docs_id
- closing_docs_set_id
- docs_manifest_json
- summary_text
- created_at
- updated_at

#### closing_docs_items
- id
- closing_docs_id
- item_code
- artifact_ref
- item_status
- created_at

#### closing_docs_flags
- id
- closing_docs_id
- flag_code
- severity
- summary
- created_at

## 6. M-043 Payment Tracker

### Canonical refs
- payment_tracking_set_id => PTS-YYYY-NNNNNN
- payment_tracking_id => PT-YYYY-NNNNNN
- payment_tracking_event_id => PTE-YYYY-NNNNNN

### Таблицы
#### payment_tracking_sets
- id
- payment_tracking_set_id
- deal_id
- payment_status
- created_at
- updated_at

#### payment_tracking_records
- id
- payment_tracking_id
- payment_tracking_set_id
- expected_amount
- paid_amount
- overdue_days
- summary_text
- created_at
- updated_at

#### payment_tracking_events
- id
- payment_tracking_event_id
- payment_tracking_id
- event_type
- event_timestamp
- summary
- source_ref
- created_at

#### payment_tracking_alerts
- id
- payment_tracking_id
- alert_code
- severity
- summary
- created_at

## 7. M-044 Claims Trigger Engine

### Canonical refs
- claim_trigger_set_id => CTS-YYYY-NNNNNN
- claim_trigger_id => CT-YYYY-NNNNNN

### Таблицы
#### claim_trigger_sets
- id
- claim_trigger_set_id
- deal_id
- trigger_status
- created_at
- updated_at

#### claim_trigger_records
- id
- claim_trigger_id
- claim_trigger_set_id
- summary_text
- trigger_reason
- created_at
- updated_at

#### claim_trigger_flags
- id
- claim_trigger_id
- flag_code
- severity
- summary
- created_at

#### claim_trigger_links
- id
- claim_trigger_id
- source_ref
- created_at

## 8. DTO contracts
### BuildLogisticsTrackingRequest
{
  "deal_id": "DL-2026-000001"
}

### BuildIncidentRegisterRequest
{
  "deal_id": "DL-2026-000001"
}

### BuildAcceptanceControlRequest
{
  "deal_id": "DL-2026-000001"
}

### BuildClosingDocsRequest
{
  "deal_id": "DL-2026-000001"
}

### BuildPaymentTrackingRequest
{
  "deal_id": "DL-2026-000001"
}

### BuildClaimTriggerRequest
{
  "deal_id": "DL-2026-000001"
}

## 9. Anti-chaos rules
1. M-039 and M-041 must remain separate even if current helper combines shipping/acceptance.
2. M-040 must remain explicit canonical incident register.
3. M-043 must remain explicit canonical payment tracker.
4. M-044 must remain explicit canonical claims trigger.
5. No new canonical IDs beyond master-registry.
