# Sprint 3B Implementation Summary

## Reused Foundation

- `M-001` deal registry and canonical `deal_id`
- `M-004` append-only event journal
- Sprint 2B analysis outputs:
  - `compliance_matrices`
  - `document_requirement_sets`
  - `initial_tech_risk_flag_sets`
- Sprint 3A supplier package:
  - `supplier_profiles`
  - `supplier_shortlists`
  - `rfq_batches`
  - `supplier_communication_sets`
  - `quote_sets`
  - `quote_records`
- shared application business ID generators and modular FastAPI / SQLAlchemy / Alembic structure

## Detected Mismatches

1. Sprint 3B source-of-truth docs were provided outside the repository, so repo-local copies are added under `docs/`.
2. The broader module cards mention refresh/orchestration flows, but the current sprint brief only requires build and query APIs. Reruns are therefore implemented as append-only rebuilds through repeated `build` calls.
3. Quote comparison needs delivery and quality dimensions, but Sprint 3A quote records do not store formal delivery terms yet. The implementation therefore uses explicit proxy scores from quote status and verification context, while keeping the dimensions separate and persisted.

## Assumptions

1. Supplier verification is built per deal context from shortlist plus supplier registry, communications, and latest quote signals.
2. Quote comparison includes all formal quote records in the provided `quote_set`; revised quotes remain distinct persisted rows and may outrank earlier ones.
3. Recommendation always points to an existing comparison row and is persisted separately.
4. Verification and comparison runs are append-only and do not overwrite prior runs.

## Exact Sprint 3B Scope

- `M-020` Supplier Verification
- `M-021` Quote Comparison Engine

Sprint 3B output is a persisted supplier quality package:

- `supplier_verification_sets`
- `supplier_verification_records`
- `supplier_verification_flags`
- `quote_comparison_sets`
- `quote_comparison_rows`
- `quote_comparison_recommendations`

## Added Business IDs

- `SVS-YYYY-NNNNNN`
- `SV-YYYY-NNNNNN`
- `QCS-YYYY-NNNNNN`

## Added Migrations

1. `019_create_supplier_verification.py`
2. `020_create_quote_comparison.py`

## Added Endpoints

- `POST /supplier-verification/build`
- `GET /supplier-verification/{supplier_verification_set_id}`
- `GET /supplier-verification`
- `GET /supplier-verification/records/{supplier_verification_id}`
- `POST /quote-comparison/build`
- `GET /quote-comparison/{quote_comparison_set_id}`
- `GET /quote-comparison`
- `GET /quote-comparison/recommendation/{quote_comparison_set_id}`

## Added Tests

- verification set build
- verification record persistence
- verification flag persistence
- quote comparison build
- comparison row persistence
- recommendation persistence
- linkage of Sprint 3B outputs to `deal_id`
- key Sprint 3B event trace coverage
- append-only rerun behavior

## Known Limitations

1. Supplier verification is heuristic and deterministic; it is not yet backed by external registries or legal-data connectors.
2. Quote comparison uses explicit proxy scores for delivery and quality until richer supplier and delivery terms are formalized.
3. No economics, margin, financing, or contract risk logic is introduced in this sprint.

## TODO For Sprint 4

1. Add `M-022` cost model engine.
2. Add `M-025` finance memo foundation when upstream economics records exist.
3. Add richer contract and integrated risk contours over supplier quality outputs.
