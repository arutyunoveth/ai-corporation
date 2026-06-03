# Sprint 6A Technical Spec
## Модули M-039, M-040, M-041, M-042, M-043, M-044

## 1. Назначение
Sprint 6A строит execution / delivery contour поверх уже готового:
- Sprint 1 foundation
- Sprint 2A intake foundation
- Sprint 2B analysis foundation
- Sprint 3A supplier-side foundation
- Sprint 3B supplier quality layer
- Sprint 4A economics layer
- Sprint 4B risk + approval layer
- Sprint 5A bid-prep foundation
- Sprint 5B submission layer

Модули:
- M-039 Delivery Launch Control
- M-040 Execution Command Center
- M-041 Delivery Milestone Tracker
- M-042 Supplier Fulfillment Tracker
- M-043 Shipping & Acceptance Tracker
- M-044 Payment Collection Tracker

## 2. Результат Sprint 6A
К концу Sprint 6A система должна уметь:
1. открывать execution context after award;
2. строить formal delivery launch control object;
3. строить central execution record for the awarded deal;
4. отслеживать milestones исполнения;
5. отслеживать supplier fulfillment against awarded package;
6. отслеживать shipment / acceptance events;
7. отслеживать invoicing / payment collection state;
8. писать event/audit trace;
9. подготовить foundation для Sprint 6B:
   - M-045 Incident & Escalation Desk
   - M-046 Deal Closure & Archive
   - M-047 KPI & Learning Loop

Итог:
из awarded outcome получить formal execution package:
delivery launch + execution command center + milestones + fulfillment + shipping/acceptance + payment collection.

## 3. Что не входит
- full incident desk
- archive/closure
- KPI/learning loop
- analytics dashboards
- advanced logistics integrations
- multi-party workflow orchestration outside current runtime

## 4. Зависимости
Использует:
- deal / event log / document store
- outcome intake from Sprint 5B
- quote_set / supplier package
- finance memo / approval where useful
- bid package and submission evidence where useful

## 5. Архитектурные принципы
1. Execution starts only from explicit awarded outcome.
2. Launch control is distinct from ongoing execution tracking.
3. Milestones are distinct from supplier fulfillment events.
4. Shipping/acceptance is distinct from payment collection.
5. Every execution-significant step emits events.
6. Execution state must remain queryable by deal.

# 6. M-039 — Delivery Launch Control

## Назначение
Open execution context after award and validate launch prerequisites.

## Сущности
- delivery_launch_sets
- delivery_launch_records
- delivery_launch_flags

## Таблицы
### delivery_launch_sets
- id
- delivery_launch_set_id (`DLS-YYYY-NNNNNN`)
- deal_id
- outcome_intake_set_id
- launch_status (`READY|BLOCKED|LAUNCHED|FAILED`)
- created_at
- updated_at

### delivery_launch_records
- id
- delivery_launch_id (`DLC-YYYY-NNNNNN`)
- delivery_launch_set_id
- launch_recommendation (`READY|BLOCKED|NEEDS_REVIEW`)
- summary_text
- created_at
- updated_at

### delivery_launch_flags
- id
- delivery_launch_id
- flag_code
- severity (`LOW|MEDIUM|HIGH|CRITICAL`)
- summary
- source_ref
- created_at

## API
- POST /delivery-launch/build
- POST /delivery-launch/launch
- GET /delivery-launch/{delivery_launch_set_id}
- GET /delivery-launch?deal_id=...
- GET /delivery-launch/records/{delivery_launch_id}

## Events
- delivery_launch_built
- delivery_launch_started
- delivery_launch_failed

# 7. M-040 — Execution Command Center

## Назначение
Central persisted execution record for awarded deal.

## Сущности
- execution_command_sets
- execution_command_records
- execution_command_bindings

## Таблицы
### execution_command_sets
- id
- execution_command_set_id (`ECS-YYYY-NNNNNN`)
- deal_id
- delivery_launch_set_id
- execution_status (`OPEN|IN_PROGRESS|COMPLETED|ON_HOLD|FAILED`)
- created_at
- updated_at

### execution_command_records
- id
- execution_command_id (`EC-YYYY-NNNNNN`)
- execution_command_set_id
- current_phase (`LAUNCHED|PROCUREMENT|SHIPPING|ACCEPTANCE|INVOICING|COLLECTION|CLOSED`)
- summary_text
- created_at
- updated_at

### execution_command_bindings
- id
- execution_command_set_id
- source_object_type (`OUTCOME|LAUNCH|SUPPLIER|PACKAGE|OTHER`)
- source_object_ref
- created_at

## API
- POST /execution/build
- GET /execution/{execution_command_set_id}
- GET /execution?deal_id=...
- GET /execution/records/{execution_command_id}

## Events
- execution_command_built
- execution_command_updated
- execution_command_failed

# 8. M-041 — Delivery Milestone Tracker

## Назначение
Track execution milestones across the awarded deal.

## Сущности
- delivery_milestone_sets
- delivery_milestone_records
- delivery_milestone_events

## Таблицы
### delivery_milestone_sets
- id
- delivery_milestone_set_id (`DMS-YYYY-NNNNNN`)
- deal_id
- execution_command_set_id
- milestone_status (`ACTIVE|COMPLETED|BLOCKED|STALE`)
- created_at
- updated_at

### delivery_milestone_records
- id
- delivery_milestone_id (`DM-YYYY-NNNNNN`)
- delivery_milestone_set_id
- milestone_code
- milestone_name
- due_date
- milestone_state (`PLANNED|IN_PROGRESS|DONE|DELAYED|CANCELLED`)
- created_at
- updated_at

### delivery_milestone_events
- id
- delivery_milestone_event_id (`DME-YYYY-NNNNNN`)
- delivery_milestone_id
- event_timestamp
- summary
- source_ref
- created_at

## API
- POST /delivery-milestones/build
- POST /delivery-milestones/events
- GET /delivery-milestones/{delivery_milestone_set_id}
- GET /delivery-milestones?deal_id=...
- GET /delivery-milestones/records/{delivery_milestone_id}

## Events
- delivery_milestones_built
- delivery_milestone_event_recorded
- delivery_milestones_failed

# 9. M-042 — Supplier Fulfillment Tracker

## Назначение
Track supplier-side fulfillment against awarded scope.

## Сущности
- supplier_fulfillment_sets
- supplier_fulfillment_records
- supplier_fulfillment_events

## Таблицы
### supplier_fulfillment_sets
- id
- supplier_fulfillment_set_id (`SFS-YYYY-NNNNNN`)
- deal_id
- execution_command_set_id
- fulfillment_status (`ACTIVE|COMPLETED|AT_RISK|FAILED`)
- created_at
- updated_at

### supplier_fulfillment_records
- id
- supplier_fulfillment_id (`SF-YYYY-NNNNNN`)
- supplier_fulfillment_set_id
- supplier_id
- fulfillment_state (`PENDING|IN_PROGRESS|FULFILLED|DELAYED|FAILED`)
- summary_text
- created_at
- updated_at

### supplier_fulfillment_events
- id
- supplier_fulfillment_event_id (`SFE-YYYY-NNNNNN`)
- supplier_fulfillment_id
- event_timestamp
- summary
- source_ref
- created_at

## API
- POST /supplier-fulfillment/build
- POST /supplier-fulfillment/events
- GET /supplier-fulfillment/{supplier_fulfillment_set_id}
- GET /supplier-fulfillment?deal_id=...
- GET /supplier-fulfillment/records/{supplier_fulfillment_id}

## Events
- supplier_fulfillment_built
- supplier_fulfillment_event_recorded
- supplier_fulfillment_failed

# 10. M-043 — Shipping & Acceptance Tracker

## Назначение
Track shipment and acceptance as persisted delivery events.

## Сущности
- shipping_acceptance_sets
- shipping_acceptance_records
- shipping_acceptance_events

## Таблицы
### shipping_acceptance_sets
- id
- shipping_acceptance_set_id (`SAS-YYYY-NNNNNN`)
- deal_id
- execution_command_set_id
- shipping_status (`ACTIVE|DELIVERED|ACCEPTED|FAILED|STALE`)
- created_at
- updated_at

### shipping_acceptance_records
- id
- shipping_acceptance_id (`SHA-YYYY-NNNNNN`)
- shipping_acceptance_set_id
- shipment_ref
- acceptance_ref
- current_state (`PLANNED|SHIPPED|DELIVERED|ACCEPTED|REJECTED`)
- created_at
- updated_at

### shipping_acceptance_events
- id
- shipping_acceptance_event_id (`SAE-YYYY-NNNNNN`)
- shipping_acceptance_id
- event_timestamp
- summary
- source_ref
- created_at

## API
- POST /shipping-acceptance/build
- POST /shipping-acceptance/events
- GET /shipping-acceptance/{shipping_acceptance_set_id}
- GET /shipping-acceptance?deal_id=...
- GET /shipping-acceptance/records/{shipping_acceptance_id}

## Events
- shipping_acceptance_built
- shipping_acceptance_event_recorded
- shipping_acceptance_failed

# 11. M-044 — Payment Collection Tracker

## Назначение
Track invoicing and collection after acceptance.

## Сущности
- payment_collection_sets
- payment_collection_records
- payment_collection_events

## Таблицы
### payment_collection_sets
- id
- payment_collection_set_id (`PCS-YYYY-NNNNNN`)
- deal_id
- execution_command_set_id
- collection_status (`ACTIVE|INVOICED|PARTIALLY_COLLECTED|COLLECTED|FAILED`)
- created_at
- updated_at

### payment_collection_records
- id
- payment_collection_id (`PC-YYYY-NNNNNN`)
- payment_collection_set_id
- invoice_ref
- expected_amount
- collected_amount
- currency_code
- collection_state (`NOT_INVOICED|INVOICED|PARTIAL|COLLECTED|OVERDUE`)
- created_at
- updated_at

### payment_collection_events
- id
- payment_collection_event_id (`PCE-YYYY-NNNNNN`)
- payment_collection_id
- event_timestamp
- summary
- source_ref
- created_at

## API
- POST /payment-collection/build
- POST /payment-collection/events
- GET /payment-collection/{payment_collection_set_id}
- GET /payment-collection?deal_id=...
- GET /payment-collection/records/{payment_collection_id}

## Events
- payment_collection_built
- payment_collection_event_recorded
- payment_collection_failed

# 12. Общие enums Sprint 6A
- DeliveryLaunchStatus = READY, BLOCKED, LAUNCHED, FAILED
- LaunchRecommendation = READY, BLOCKED, NEEDS_REVIEW
- ExecutionCommandStatus = OPEN, IN_PROGRESS, COMPLETED, ON_HOLD, FAILED
- ExecutionPhase = LAUNCHED, PROCUREMENT, SHIPPING, ACCEPTANCE, INVOICING, COLLECTION, CLOSED
- DeliveryMilestoneStatus = ACTIVE, COMPLETED, BLOCKED, STALE
- MilestoneState = PLANNED, IN_PROGRESS, DONE, DELAYED, CANCELLED
- SupplierFulfillmentStatus = ACTIVE, COMPLETED, AT_RISK, FAILED
- SupplierFulfillmentState = PENDING, IN_PROGRESS, FULFILLED, DELAYED, FAILED
- ShippingAcceptanceStatus = ACTIVE, DELIVERED, ACCEPTED, FAILED, STALE
- ShippingAcceptanceState = PLANNED, SHIPPED, DELIVERED, ACCEPTED, REJECTED
- PaymentCollectionStatus = ACTIVE, INVOICED, PARTIALLY_COLLECTED, COLLECTED, FAILED
- CollectionState = NOT_INVOICED, INVOICED, PARTIAL, COLLECTED, OVERDUE

# 13. Поток Sprint 6A
awarded outcome
  -> delivery launch
  -> execution command center
  -> milestones
  -> supplier fulfillment
  -> shipping/acceptance
  -> payment collection
  -> ready for closure / incidents / learning

# 14. Migration order Sprint 6A
- Migration 036: delivery launch tables
- Migration 037: execution command tables
- Migration 038: delivery milestone tables
- Migration 039: supplier fulfillment tables
- Migration 040: shipping acceptance tables
- Migration 041: payment collection tables

# 15. Acceptance criteria по всему Sprint 6A
1. delivery launch formalized;
2. execution command center formalized;
3. milestones formalized;
4. supplier fulfillment formalized;
5. shipping/acceptance formalized;
6. payment collection formalized;
7. all outputs linked to deal;
8. event trace preserved;
9. foundation ready for Sprint 6B closure / incidents / learning.
