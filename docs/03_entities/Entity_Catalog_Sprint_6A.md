# Entity Catalog Sprint 6A
## Модули M-039, M-040, M-041, M-042, M-043, M-044

## 1. Назначение
Единый каталог сущностей Sprint 6A.

## 2. Scope
Покрывает:
- M-039 Delivery Launch Control
- M-040 Execution Command Center
- M-041 Delivery Milestone Tracker
- M-042 Supplier Fulfillment Tracker
- M-043 Shipping & Acceptance Tracker
- M-044 Payment Collection Tracker

Опирается на:
- deal
- outcome_intake_set
- quote_set / supplier package
- finance memo / approval where useful
- document_artifact
- event_record

## 3. Canonical refs
- delivery_launch_set_id => DLS-YYYY-NNNNNN
- delivery_launch_id => DLC-YYYY-NNNNNN
- execution_command_set_id => ECS-YYYY-NNNNNN
- execution_command_id => EC-YYYY-NNNNNN
- delivery_milestone_set_id => DMS-YYYY-NNNNNN
- delivery_milestone_id => DM-YYYY-NNNNNN
- delivery_milestone_event_id => DME-YYYY-NNNNNN
- supplier_fulfillment_set_id => SFS-YYYY-NNNNNN
- supplier_fulfillment_id => SF-YYYY-NNNNNN
- supplier_fulfillment_event_id => SFE-YYYY-NNNNNN
- shipping_acceptance_set_id => SAS-YYYY-NNNNNN
- shipping_acceptance_id => SHA-YYYY-NNNNNN
- shipping_acceptance_event_id => SAE-YYYY-NNNNNN
- payment_collection_set_id => PCS-YYYY-NNNNNN
- payment_collection_id => PC-YYYY-NNNNNN
- payment_collection_event_id => PCE-YYYY-NNNNNN

## 4. Инварианты
1. Execution starts only from explicit awarded outcome.
2. Launch control is distinct from execution command center.
3. Milestones, fulfillment, shipping and collection remain separate persisted layers.
4. All execution objects must link to deal_id.
5. New runs and events are append-only.

# 5. M-039 entities
## delivery_launch_set
- id
- delivery_launch_set_id
- deal_id
- outcome_intake_set_id
- launch_status
- created_at
- updated_at

## delivery_launch_record
- id
- delivery_launch_id
- delivery_launch_set_id
- launch_recommendation
- summary_text
- created_at
- updated_at

## delivery_launch_flag
- id
- delivery_launch_id
- flag_code
- severity
- summary
- source_ref
- created_at

# 6. M-040 entities
## execution_command_set
- id
- execution_command_set_id
- deal_id
- delivery_launch_set_id
- execution_status
- created_at
- updated_at

## execution_command_record
- id
- execution_command_id
- execution_command_set_id
- current_phase
- summary_text
- created_at
- updated_at

## execution_command_binding
- id
- execution_command_set_id
- source_object_type
- source_object_ref
- created_at

# 7. M-041 entities
## delivery_milestone_set
- id
- delivery_milestone_set_id
- deal_id
- execution_command_set_id
- milestone_status
- created_at
- updated_at

## delivery_milestone_record
- id
- delivery_milestone_id
- delivery_milestone_set_id
- milestone_code
- milestone_name
- due_date
- milestone_state
- created_at
- updated_at

## delivery_milestone_event
- id
- delivery_milestone_event_id
- delivery_milestone_id
- event_timestamp
- summary
- source_ref
- created_at

# 8. M-042 entities
## supplier_fulfillment_set
- id
- supplier_fulfillment_set_id
- deal_id
- execution_command_set_id
- fulfillment_status
- created_at
- updated_at

## supplier_fulfillment_record
- id
- supplier_fulfillment_id
- supplier_fulfillment_set_id
- supplier_id
- fulfillment_state
- summary_text
- created_at
- updated_at

## supplier_fulfillment_event
- id
- supplier_fulfillment_event_id
- supplier_fulfillment_id
- event_timestamp
- summary
- source_ref
- created_at

# 9. M-043 entities
## shipping_acceptance_set
- id
- shipping_acceptance_set_id
- deal_id
- execution_command_set_id
- shipping_status
- created_at
- updated_at

## shipping_acceptance_record
- id
- shipping_acceptance_id
- shipping_acceptance_set_id
- shipment_ref
- acceptance_ref
- current_state
- created_at
- updated_at

## shipping_acceptance_event
- id
- shipping_acceptance_event_id
- shipping_acceptance_id
- event_timestamp
- summary
- source_ref
- created_at

# 10. M-044 entities
## payment_collection_set
- id
- payment_collection_set_id
- deal_id
- execution_command_set_id
- collection_status
- created_at
- updated_at

## payment_collection_record
- id
- payment_collection_id
- payment_collection_set_id
- invoice_ref
- expected_amount
- collected_amount
- currency_code
- collection_state
- created_at
- updated_at

## payment_collection_event
- id
- payment_collection_event_id
- payment_collection_id
- event_timestamp
- summary
- source_ref
- created_at

# 11. DTO contracts
BuildDeliveryLaunchRequest:
{
  "deal_id": "DL-2026-000001",
  "outcome_intake_set_id": "OIS-2026-000001"
}

BuildExecutionCommandRequest:
{
  "deal_id": "DL-2026-000001",
  "delivery_launch_set_id": "DLS-2026-000001"
}

BuildDeliveryMilestonesRequest:
{
  "deal_id": "DL-2026-000001",
  "execution_command_set_id": "ECS-2026-000001"
}

BuildSupplierFulfillmentRequest:
{
  "deal_id": "DL-2026-000001",
  "execution_command_set_id": "ECS-2026-000001"
}

BuildShippingAcceptanceRequest:
{
  "deal_id": "DL-2026-000001",
  "execution_command_set_id": "ECS-2026-000001"
}

BuildPaymentCollectionRequest:
{
  "deal_id": "DL-2026-000001",
  "execution_command_set_id": "ECS-2026-000001"
}

# 12. Migration order
- 036 delivery launch
- 037 execution command
- 038 delivery milestones
- 039 supplier fulfillment
- 040 shipping acceptance
- 041 payment collection

# 13. Anti-chaos rules
1. Do not open execution without explicit awarded outcome.
2. Do not merge launch control and execution command center.
3. Do not merge shipping/acceptance with payment collection.
4. Do not overwrite prior events or state snapshots; append new records.
