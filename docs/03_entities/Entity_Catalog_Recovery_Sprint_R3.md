# Entity Catalog Recovery Sprint R3
## Канонические модули M-035, M-036, M-037, M-038

## 1. Назначение
Единый каталог сущностей для controlled recovery step R3.

## 2. M-035 Supplier Back-to-Back Contract Draft

### Canonical refs
- supplier_contract_set_id => SCS-YYYY-NNNNNN
- supplier_contract_id => SC-YYYY-NNNNNN

### Таблицы
#### supplier_contract_sets
- id
- supplier_contract_set_id
- deal_id
- supplier_id
- contract_status
- created_at
- updated_at

#### supplier_contract_records
- id
- supplier_contract_id
- supplier_contract_set_id
- summary_text
- contract_manifest_json
- created_at
- updated_at

#### supplier_contract_obligations
- id
- supplier_contract_id
- obligation_code
- obligation_text
- obligation_status
- created_at

#### supplier_contract_comments
- id
- supplier_contract_id
- clause_ref
- comment_text
- created_at

## 3. M-036 Execution Plan Builder

### Canonical refs
- execution_plan_set_id => EPS-YYYY-NNNNNN
- execution_plan_id => EP-YYYY-NNNNNN
- execution_plan_milestone_id => EPM-YYYY-NNNNNN

### Таблицы
#### execution_plan_sets
- id
- execution_plan_set_id
- deal_id
- plan_status
- created_at
- updated_at

#### execution_plan_records
- id
- execution_plan_id
- execution_plan_set_id
- summary_text
- baseline_manifest_json
- created_at
- updated_at

#### execution_plan_milestones
- id
- execution_plan_milestone_id
- execution_plan_id
- milestone_code
- milestone_name
- due_date
- milestone_state
- created_at
- updated_at

#### execution_plan_assumptions
- id
- execution_plan_id
- assumption_code
- assumption_text
- created_at

## 4. M-037 Purchase Order Manager

### Canonical refs
- purchase_order_set_id => POS-YYYY-NNNNNN
- purchase_order_id => PO-YYYY-NNNNNN

### Таблицы
#### purchase_order_sets
- id
- purchase_order_set_id
- deal_id
- supplier_id
- po_status
- created_at
- updated_at

#### purchase_order_records
- id
- purchase_order_id
- purchase_order_set_id
- po_number
- summary_text
- created_at
- updated_at

#### purchase_order_items
- id
- purchase_order_id
- item_code
- item_description
- quantity
- created_at

#### purchase_order_links
- id
- purchase_order_id
- source_ref
- created_at

## 5. M-038 Supplier Progress Monitor

### Canonical refs
- supplier_progress_set_id => SPS-YYYY-NNNNNN
- supplier_progress_id => SP-YYYY-NNNNNN
- supplier_progress_event_id => SPE-YYYY-NNNNNN

### Таблицы
#### supplier_progress_sets
- id
- supplier_progress_set_id
- deal_id
- supplier_id
- progress_status
- created_at
- updated_at

#### supplier_progress_records
- id
- supplier_progress_id
- supplier_progress_set_id
- readiness_state
- summary_text
- created_at
- updated_at

#### supplier_progress_events
- id
- supplier_progress_event_id
- supplier_progress_id
- event_type
- event_timestamp
- summary
- source_ref
- created_at

#### supplier_progress_alerts
- id
- supplier_progress_id
- alert_code
- severity
- summary
- created_at

## 6. DTO contracts
### BuildSupplierContractRequest
{
  "deal_id": "DL-2026-000001",
  "supplier_id": "SUP-2026-000001"
}

### BuildExecutionPlanRequest
{
  "deal_id": "DL-2026-000001"
}

### BuildPurchaseOrderRequest
{
  "deal_id": "DL-2026-000001",
  "supplier_id": "SUP-2026-000001"
}

### BuildSupplierProgressRequest
{
  "deal_id": "DL-2026-000001",
  "supplier_id": "SUP-2026-000001"
}

## 7. Anti-chaos rules
1. M-036 Execution Plan Builder must remain separate from helper milestone/execution contours.
2. M-037 Purchase Order Manager must remain explicit canonical supplier order module.
3. M-038 Supplier Progress Monitor must remain separate from supplier fulfillment helper.
4. No new canonical IDs beyond master-registry.
