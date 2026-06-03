# Entity Catalog Sprint 4B
## Modules M-026, M-027, M-028

## Canonical Refs
- `contract_risk_set_id => CRS-YYYY-NNNNNN`
- `contract_risk_id => CR-YYYY-NNNNNN`
- `integrated_risk_memo_set_id => IRMS-YYYY-NNNNNN`
- `integrated_risk_memo_id => IRM-YYYY-NNNNNN`
- `ceo_approval_set_id => CAS-YYYY-NNNNNN`
- `ceo_approval_id => CA-YYYY-NNNNNN`

## Invariants
1. Contract risk links to `deal_id` and `document_set_id`.
2. Integrated risk memo depends on upstream persisted layers.
3. Approval package depends on persisted finance memo and integrated risk memo.
4. Human decision is explicit and append-only.
5. Recommendation and final decision are never collapsed into one field.

## Entities
### contract_risk_set
- `contract_risk_set_id`
- `deal_id`
- `document_set_id`
- `risk_status`
- `created_at`
- `updated_at`

### contract_risk_record
- `contract_risk_id`
- `contract_risk_set_id`
- `source_artifact_ref`
- `clause_type`
- `summary`
- `severity`
- `notes`
- `created_at`
- `updated_at`

### contract_risk_flag
- `contract_risk_id`
- `flag_code`
- `severity`
- `summary`
- `source_ref`
- `created_at`

### integrated_risk_memo_set
- `integrated_risk_memo_set_id`
- `deal_id`
- `initial_tech_risk_flag_set_id`
- `supplier_verification_set_id`
- `quote_comparison_set_id`
- `finance_memo_set_id`
- `contract_risk_set_id`
- `memo_status`
- `created_at`
- `updated_at`

### integrated_risk_memo_record
- `integrated_risk_memo_id`
- `integrated_risk_memo_set_id`
- `summary_text`
- `structured_summary_json`
- `recommendation`
- `created_at`
- `updated_at`

### integrated_risk_item
- `integrated_risk_memo_id`
- `risk_source_type`
- `source_object_ref`
- `severity`
- `summary`
- `mitigation_hint`
- `created_at`

### ceo_approval_set
- `ceo_approval_set_id`
- `deal_id`
- `finance_memo_set_id`
- `integrated_risk_memo_set_id`
- `approval_status`
- `created_at`
- `updated_at`

### ceo_approval_record
- `ceo_approval_id`
- `ceo_approval_set_id`
- `decision`
- `decided_by_ref`
- `rationale`
- `decided_at`
- `created_at`
- `updated_at`

### ceo_approval_condition
- `ceo_approval_id`
- `condition_code`
- `condition_text`
- `created_at`
