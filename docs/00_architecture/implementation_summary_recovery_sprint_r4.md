# Implementation Summary Recovery Sprint R4

## Reused Foundation

- Recovery governance layer and canonical registry lock from `docs/99_governance/*`
- Existing execution-entry contour:
  - `supplier_contracts`
  - `execution_plans`
  - `purchase_orders`
  - `supplier_progress`
- Existing delivery/payment helper contour:
  - `delivery_launch`
  - `execution_command`
  - `delivery_milestones`
  - `supplier_fulfillment`
  - `shipping_acceptance`
  - `payment_collection`
  - `incidents`

## Implemented Canonical Modules

- `M-039` Logistics Tracker
  - implemented as `logistics_tracking_sets`, `logistics_tracking_records`, `logistics_tracking_events`, `logistics_tracking_links`
- `M-040` Incident Register
  - implemented as `incident_register_sets`, `incident_register_records`, `incident_register_events`, `incident_register_flags`
- `M-041` Acceptance Control
  - implemented as `acceptance_control_sets`, `acceptance_control_records`, `acceptance_remarks`, `acceptance_resolution_items`
- `M-042` Closing Docs Pack Builder
  - implemented as `closing_docs_sets`, `closing_docs_records`, `closing_docs_items`, `closing_docs_flags`
- `M-043` Payment Tracker
  - implemented as `payment_tracking_sets`, `payment_tracking_records`, `payment_tracking_events`, `payment_tracking_alerts`
- `M-044` Claims Trigger Engine
  - implemented as `claim_trigger_sets`, `claim_trigger_records`, `claim_trigger_flags`, `claim_trigger_links`

## Assumptions / Detected Mismatches

1. The recovery entity catalog fixes `acceptance_control_set_id` to `ACS-YYYY-NNNNNN`, which overlaps by prefix with a non-canonical action-console helper set. This overlap is retained intentionally because refs remain entity-scoped and the locked recovery docs forbid inventing a new canonical prefix.
2. Existing `shipping_acceptance`, `payment_collection`, and `incidents` contours remain runtime helpers and do not replace canonical `M-039..M-044`.
3. `M-039` and `M-041` remain separate canonical layers even though helper shipping/acceptance data is combined in one legacy support contour.
4. `M-044` is surfaced as an explicit canonical claim-trigger artifact rather than hidden inside payment or incident helper logic.

## Migrations

- `073_create_logistics_tracking`
- `074_create_incident_register`
- `075_create_acceptance_control`
- `076_create_closing_docs`
- `077_create_payment_tracking`
- `078_create_claim_triggers`

## Endpoints

- `POST /logistics-tracking/build`
- `POST /logistics-tracking/events`
- `GET /logistics-tracking/{logistics_tracking_set_id}`
- `GET /logistics-tracking`
- `GET /logistics-tracking/records/{logistics_tracking_id}`
- `POST /incident-register/build`
- `POST /incident-register/events`
- `GET /incident-register/{incident_register_set_id}`
- `GET /incident-register`
- `GET /incident-register/records/{incident_register_id}`
- `POST /acceptance-control/build`
- `GET /acceptance-control/{acceptance_control_set_id}`
- `GET /acceptance-control`
- `GET /acceptance-control/records/{acceptance_control_id}`
- `POST /closing-docs/build`
- `GET /closing-docs/{closing_docs_set_id}`
- `GET /closing-docs`
- `GET /closing-docs/records/{closing_docs_id}`
- `POST /payment-tracking/build`
- `POST /payment-tracking/events`
- `GET /payment-tracking/{payment_tracking_set_id}`
- `GET /payment-tracking`
- `GET /payment-tracking/records/{payment_tracking_id}`
- `POST /claim-triggers/build`
- `GET /claim-triggers/{claim_trigger_set_id}`
- `GET /claim-triggers`
- `GET /claim-triggers/records/{claim_trigger_id}`

## Tests Added

- logistics tracking build and event/link persistence
- incident register build and event/flag persistence
- acceptance control build and remark/resolution persistence
- closing docs build and item/flag persistence
- payment tracking build and event/alert persistence
- claim trigger build and flag/link persistence
- linkage to canonical deal plus delivery/payment context
- key R4 events written to event log
- append-only rerun behavior for claim trigger build

## Verification

- `pytest tests/test_recovery_r4_integration.py -q` -> `6 passed`
- `pytest -q` -> `158 passed`
- `AI_CORP_DATABASE_URL=sqlite+pysqlite:///./recovery_r4_verify.db alembic upgrade head` -> success

## Governance Result

- Canonical coverage is now exact for `M-039`, `M-040`, `M-041`, `M-042`, `M-043`, and `M-044`.
- Remaining registry drift is now concentrated in `M-045..M-050` and `M-052..M-055`.
- Delivery, acceptance, payment, and claim recovery are represented by canonical business modules rather than helper replacements.
