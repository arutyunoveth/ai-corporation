# Entity Catalog Sprint 3A

## Canonical Refs

- `supplier_id` => `SUP-YYYY-NNNNNN`
- `supplier_shortlist_id` => `SSL-YYYY-NNNNNN`
- `rfq_batch_id` => `RB-YYYY-NNNNNN`
- `rfq_id` => `RFQ-YYYY-NNNNNN`
- `supplier_communication_set_id` => `SCS-YYYY-NNNNNN`
- `supplier_thread_id` => `SCT-YYYY-NNNNNN`
- `supplier_message_id` => `SM-YYYY-NNNNNN`
- `quote_set_id` => `QS-YYYY-NNNNNN`
- `quote_id` => `Q-YYYY-NNNNNN`

## Global Invariants

1. Any supplier-side record is linked to `deal_id` directly or through a persisted header object.
2. Supplier identity is based on `supplier_id`, not free text.
3. RFQ cannot be built without an existing shortlist.
4. Quote must reference at least `supplier_id`, `rfq_id`, and deal through a header object.
5. Every supplier-side operation writes event trace.

## `M-006`

### `supplier_profiles`

- `supplier_id`
- `legal_name`
- `display_name`
- `inn`
- `country_code`
- `status`
- `notes`
- `created_at`
- `updated_at`

Invariants:

- `supplier_id` unique
- `inn` unique

### `supplier_external_refs`

- `supplier_id`
- `ref_type`
- `ref_value`
- `created_at`

### `supplier_contacts`

- `supplier_id`
- `contact_name`
- `email`
- `phone`
- `is_primary`
- `created_at`

### `supplier_tags`

- `supplier_id`
- `tag_code`
- `created_at`

Enum `SupplierStatus`:

- `ACTIVE`
- `INACTIVE`
- `BLACKLISTED`
- `DRAFT`

## `M-016`

### `supplier_shortlists`

- `supplier_shortlist_id`
- `deal_id`
- `intake_id`
- `document_set_id`
- `tender_summary_id`
- `shortlist_status`
- `created_at`
- `updated_at`

### `supplier_shortlist_rows`

- `supplier_shortlist_id`
- `supplier_id`
- `rank_order`
- `inclusion_reason`
- `source_type`
- `created_at`

Enum `SupplierShortlistStatus`:

- `BUILT`
- `FAILED`
- `STALE`

## `M-017`

### `rfq_batches`

- `rfq_batch_id`
- `deal_id`
- `supplier_shortlist_id`
- `batch_status`
- `created_at`
- `updated_at`

### `rfq_records`

- `rfq_id`
- `rfq_batch_id`
- `supplier_id`
- `subject`
- `body_text`
- `rfq_status`
- `created_at`
- `updated_at`

### `rfq_artifact_bindings`

- `rfq_id`
- `artifact_ref`
- `created_at`

Enum `RFQBatchStatus`:

- `BUILT`
- `READY_TO_SEND`
- `SENT`
- `PARTIAL`
- `FAILED`

Enum `RFQStatus`:

- `BUILT`
- `SENT`
- `REPLIED`
- `CLOSED`

## `M-018`

### `supplier_communication_sets`

- `supplier_communication_set_id`
- `deal_id`
- `rfq_batch_id`
- `created_at`

### `supplier_communication_threads`

- `supplier_thread_id`
- `supplier_communication_set_id`
- `supplier_id`
- `rfq_id`
- `thread_status`
- `last_message_at`
- `created_at`

### `supplier_message_records`

- `supplier_message_id`
- `supplier_thread_id`
- `direction`
- `message_subject`
- `message_text`
- `linked_artifact_ref`
- `sent_at`
- `created_at`

Enum `SupplierThreadStatus`:

- `OPEN`
- `WAITING_REPLY`
- `REPLIED`
- `CLOSED`

Enum `MessageDirection`:

- `OUTBOUND`
- `INBOUND`

## `M-019`

### `quote_sets`

- `quote_set_id`
- `deal_id`
- `rfq_batch_id`
- `created_at`

### `quote_records`

- `quote_id`
- `quote_set_id`
- `supplier_id`
- `rfq_id`
- `supplier_thread_id`
- `quote_status`
- `quoted_amount`
- `currency_code`
- `quoted_at`
- `notes`
- `created_at`
- `updated_at`

### `quote_artifact_bindings`

- `quote_id`
- `artifact_ref`
- `created_at`

Enum `QuoteStatus`:

- `RECEIVED`
- `REVISED`
- `WITHDRAWN`
