# Sprint 3B Technical Spec

## Modules

- `M-020` Supplier Verification
- `M-021` Quote Comparison Engine

## Goal

Sprint 3B adds the supplier quality layer on top of:

- Sprint 1 foundation
- Sprint 2A intake foundation
- Sprint 2B analysis foundation
- Sprint 3A supplier-side foundation

By the end of the sprint the system must be able to:

1. build formal supplier verification runs;
2. persist per-supplier verification results and flags;
3. build quote comparison only from formal quote records;
4. persist ranking and recommendation;
5. preserve event and audit trace;
6. prepare foundation for Sprint 4 economics, risk, and approval.

## Non-Goals

- cost model
- cash gap
- financing strategy
- finance memo
- contract risk parser
- approval cockpit
- bid prep
- execution

## Dependencies

- `deal`, `event log`, `document store`
- analysis package from Sprint 2B
- supplier registry, shortlist, RFQ, communications, and quotes from Sprint 3A

## Architectural Principles

1. Verification is a persisted business object.
2. Quote comparison is built only from formal quote records.
3. Quality and price remain separable dimensions.
4. Comparison must be explainable.
5. Every business-significant step leaves event trace.

## API Scope

### `M-020`

- `POST /supplier-verification/build`
- `GET /supplier-verification/{supplier_verification_set_id}`
- `GET /supplier-verification`
- `GET /supplier-verification/records/{supplier_verification_id}`

### `M-021`

- `POST /quote-comparison/build`
- `GET /quote-comparison/{quote_comparison_set_id}`
- `GET /quote-comparison`
- `GET /quote-comparison/recommendation/{quote_comparison_set_id}`

## Event Codes

- `supplier_verification_build_started`
- `supplier_verification_built`
- `supplier_verification_failed`
- `quote_comparison_build_started`
- `quote_comparison_built`
- `quote_comparison_failed`

## Migration Order

1. `019_create_supplier_verification`
2. `020_create_quote_comparison`

## Acceptance Criteria

1. Supplier verification is formalized.
2. Quote comparison is formalized.
3. Ranking and recommendation are persisted.
4. All outputs are linked to `deal_id`.
5. Event trace is preserved.
6. Foundation is ready for Sprint 4 economics, risk, and approval.
