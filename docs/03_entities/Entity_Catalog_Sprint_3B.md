# Entity Catalog Sprint 3B

## Canonical Refs

- `supplier_verification_set_id` => `SVS-YYYY-NNNNNN`
- `supplier_verification_id` => `SV-YYYY-NNNNNN`
- `quote_comparison_set_id` => `QCS-YYYY-NNNNNN`

## Global Invariants

1. Verification and comparison always link to `deal_id`.
2. Comparison cannot be built without a formal `quote_set`.
3. Recommendation cannot exist without comparison rows.
4. Verification flags are append-only.
5. Every run emits events.

## `M-020`

### `supplier_verification_sets`

- `supplier_verification_set_id`
- `deal_id`
- `supplier_shortlist_id`
- `verification_status`
- `created_at`
- `updated_at`

### `supplier_verification_records`

- `supplier_verification_id`
- `supplier_verification_set_id`
- `supplier_id`
- `verification_result`
- `confidence_score`
- `notes`
- `created_at`
- `updated_at`

### `supplier_verification_flags`

- `supplier_verification_id`
- `flag_code`
- `severity`
- `summary`
- `source_ref`
- `created_at`

Enum `SupplierVerificationStatus`:

- `BUILT`
- `PARTIAL`
- `FAILED`

Enum `SupplierVerificationResult`:

- `PASS`
- `FAIL`
- `NEEDS_REVIEW`

Enum `VerificationFlagSeverity`:

- `LOW`
- `MEDIUM`
- `HIGH`
- `CRITICAL`

## `M-021`

### `quote_comparison_sets`

- `quote_comparison_set_id`
- `deal_id`
- `quote_set_id`
- `supplier_verification_set_id`
- `comparison_status`
- `created_at`
- `updated_at`

### `quote_comparison_rows`

- `quote_comparison_set_id`
- `quote_id`
- `supplier_id`
- `price_score`
- `delivery_score`
- `quality_score`
- `total_score`
- `rank_order`
- `comparison_notes`
- `created_at`

### `quote_comparison_recommendations`

- `quote_comparison_set_id`
- `recommended_quote_id`
- `recommended_supplier_id`
- `rationale`
- `created_at`

Enum `QuoteComparisonStatus`:

- `BUILT`
- `FAILED`
- `STALE`
