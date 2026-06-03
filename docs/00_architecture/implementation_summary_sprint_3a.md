# Sprint 3A Implementation Summary

## Reused Foundation

- `M-001` deal registry and canonical `deal_id`
- `M-003` artifact backbone and `artifact_ref`
- `M-004` append-only event journal
- Sprint 2A intake package:
  - `tender_intake_records`
  - `document_sets`
  - `tender_summaries`
- Sprint 2B analysis package:
  - `compliance_matrices`
  - `document_requirement_sets`
  - `initial_tech_risk_flag_sets`
- shared business ID generator pattern `PREFIX-YYYY-NNNNNN`
- modular `FastAPI + SQLAlchemy 2 + Alembic + Pydantic + pytest` structure

## Detected Mismatches

1. Official Sprint 3A source-of-truth files were provided outside the repo, so the sprint adds repo-local copies under `docs/`.
2. `rfq_batch_sent` exists in the spec, but there is still no safe automatic outbound transport. The implementation marks a batch as `SENT` only when actual outbound supplier messages are explicitly recorded.
3. Supplier search in this iteration is registry-based and heuristic, because no external supplier discovery connector exists yet.

## Assumptions

1. Supplier creation is soft-idempotent by `inn`: the existing supplier profile is reused and surfaced with `duplicate_hint`.
2. Shortlist build depends on the persisted analysis package and can optionally use Sprint 2B artifacts when available.
3. Quotes require formal header objects and at least one bound quote artifact.
4. Sprint 3A records are append-only where business history matters:
   - shortlist reruns create new shortlist headers;
   - RFQ reruns create new batches;
   - quote revisions create new quote records.

## Exact Sprint 3A Scope

- `M-006` Supplier Registry
- `M-016` Supplier Search
- `M-017` RFQ Generator
- `M-018` Supplier Communication Tracker
- `M-019` TKP Repository

Sprint 3A output is a formal supplier package built on top of the persisted analysis package:

- `supplier_profiles`
- `supplier_external_refs`
- `supplier_contacts`
- `supplier_tags`
- `supplier_shortlists`
- `supplier_shortlist_rows`
- `rfq_batches`
- `rfq_records`
- `rfq_artifact_bindings`
- `supplier_communication_sets`
- `supplier_communication_threads`
- `supplier_message_records`
- `quote_sets`
- `quote_records`
- `quote_artifact_bindings`

## Added Business IDs

- `SUP-YYYY-NNNNNN`
- `SSL-YYYY-NNNNNN`
- `RB-YYYY-NNNNNN`
- `RFQ-YYYY-NNNNNN`
- `SCS-YYYY-NNNNNN`
- `SCT-YYYY-NNNNNN`
- `SM-YYYY-NNNNNN`
- `QS-YYYY-NNNNNN`
- `Q-YYYY-NNNNNN`

## Added Migrations

1. `014_create_supplier_registry.py`
2. `015_create_supplier_shortlists.py`
3. `016_create_rfq_tables.py`
4. `017_create_supplier_communications.py`
5. `018_create_quote_repository.py`

## Added Endpoints

- `POST /suppliers`
- `GET /suppliers/{supplier_id}`
- `GET /suppliers`
- `PATCH /suppliers/{supplier_id}`
- `POST /suppliers/{supplier_id}/contacts`
- `POST /suppliers/{supplier_id}/tags`
- `POST /supplier-search/build`
- `GET /supplier-search/{supplier_shortlist_id}`
- `GET /supplier-search`
- `POST /rfq/batches/build`
- `GET /rfq/batches/{rfq_batch_id}`
- `GET /rfq/batches`
- `GET /rfq/records/{rfq_id}`
- `POST /supplier-communications/sets/build`
- `GET /supplier-communications/sets/{supplier_communication_set_id}`
- `GET /supplier-communications/sets`
- `POST /supplier-communications/threads/{supplier_thread_id}/messages`
- `GET /supplier-communications/threads/{supplier_thread_id}`
- `POST /quotes/register`
- `GET /quotes/{quote_id}`
- `GET /quotes`
- `GET /quote-sets/{quote_set_id}`

## Added Tests

- supplier profile creation
- unique `supplier_id` generation
- duplicate supplier reuse by `inn`
- shortlist build from analysis package
- shortlist row persistence
- RFQ batch and RFQ record persistence
- communication set and per-supplier threads
- outbound and inbound message recording
- quote registration and quote revision path
- linkage of supplier-side outputs to `deal_id`
- event trace coverage for key supplier-side operations

## Known Limitations

1. Supplier search is registry-only and does not use external catalog or web search.
2. RFQ generation produces persisted objects and readiness state, but does not perform real outbound delivery.
3. Communication tracking is explicit and manual in this iteration.
4. Quote registration is header-based and artifact-backed, but there is no price normalization or comparison logic yet.

## TODO For Sprint 3B

1. Add `M-020` supplier verification.
2. Add `M-021` quote comparison engine.
3. Build supplier scoring and verification enrichment.
4. Add structured quote comparison inputs for finance and cost modeling.
