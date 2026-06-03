# Sprint 3A Technical Spec

## Modules

- `M-006` Supplier Registry
- `M-016` Supplier Search
- `M-017` RFQ Generator
- `M-018` Supplier Communication Tracker
- `M-019` TKP Repository

## Goal

Sprint 3A builds supplier-side foundation on top of the already implemented:

- Sprint 1 foundation
- Sprint 2A intake foundation
- Sprint 2B analysis foundation

By the end of the sprint the system must be able to:

1. store canonical supplier profiles;
2. build a persisted supplier shortlist from the analysis package;
3. generate a formal RFQ batch from the shortlist;
4. track outbound and inbound supplier communications;
5. register supplier quotes as formal business records;
6. write event and audit trace for the supplier-side contour;
7. prepare foundation for `M-020` and `M-021`.

## Non-Goals

- supplier verification
- quote comparison
- finance / risk / approval contour
- bid prep and submission
- execution branch
- broad UI work

## Dependencies

- `M-001`, `M-002`, `M-003`, `M-004`
- `M-008`, `M-011`, `M-012`
- `M-009`, `M-010`, `M-013`, `M-014`, `M-015`

## Architectural Principles

1. Supplier-side starts from a formal analysis package.
2. Supplier is a reusable registry entity.
3. RFQ is a formal persisted business object.
4. Communication is tracked explicitly, not inferred.
5. Quotes are business records, not only artifacts.

## API Scope

### `M-006`

- `POST /suppliers`
- `GET /suppliers/{supplier_id}`
- `GET /suppliers`
- `PATCH /suppliers/{supplier_id}`
- `POST /suppliers/{supplier_id}/contacts`
- `POST /suppliers/{supplier_id}/tags`

### `M-016`

- `POST /supplier-search/build`
- `GET /supplier-search/{supplier_shortlist_id}`
- `GET /supplier-search`

### `M-017`

- `POST /rfq/batches/build`
- `GET /rfq/batches/{rfq_batch_id}`
- `GET /rfq/batches`
- `GET /rfq/records/{rfq_id}`

### `M-018`

- `POST /supplier-communications/sets/build`
- `GET /supplier-communications/sets/{supplier_communication_set_id}`
- `GET /supplier-communications/sets`
- `POST /supplier-communications/threads/{supplier_thread_id}/messages`
- `GET /supplier-communications/threads/{supplier_thread_id}`

### `M-019`

- `POST /quotes/register`
- `GET /quotes/{quote_id}`
- `GET /quotes`
- `GET /quote-sets/{quote_set_id}`

## Event Codes

- `supplier_profile_created`
- `supplier_profile_updated`
- `supplier_shortlist_build_started`
- `supplier_shortlist_built`
- `supplier_shortlist_failed`
- `rfq_batch_build_started`
- `rfq_batch_built`
- `rfq_batch_sent`
- `rfq_batch_failed`
- `supplier_communication_set_created`
- `supplier_message_recorded`
- `supplier_reply_received`
- `quote_registered`
- `quote_revised`
- `quote_withdrawn`

## Migration Order

1. `014_create_supplier_registry`
2. `015_create_supplier_shortlists`
3. `016_create_rfq_tables`
4. `017_create_supplier_communications`
5. `018_create_quote_repository`

## Acceptance Criteria

1. Supplier profiles are formalized and reusable.
2. Shortlist is built from the analysis package.
3. RFQ batch is built from the shortlist.
4. Communication threads and messages are queryable.
5. Quotes are registered formally and linked to supplier, RFQ, and thread.
6. All supplier-side outputs are linked to `deal_id`.
7. Events are written to `M-004`.
8. Foundation is ready for `M-020` and `M-021`.
