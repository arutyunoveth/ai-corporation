# Entity Catalog Sprint 5A
## Modules M-029, M-030, M-031, M-032

## Canonical Refs
- `bid_document_collection_set_id => BDCS-YYYY-NNNNNN`
- `bid_package_set_id => BPS-YYYY-NNNNNN`
- `bid_package_id => BP-YYYY-NNNNNN`
- `bid_completeness_set_id => BCS-YYYY-NNNNNN`
- `bid_completeness_id => BC-YYYY-NNNNNN`
- `submission_readiness_set_id => SRS-YYYY-NNNNNN`
- `submission_readiness_id => SR-YYYY-NNNNNN`

## Invariants
1. Collection, package, completeness, and readiness always link to `deal_id`.
2. Package depends on formal collection set.
3. Completeness depends on formal package set.
4. Readiness depends on completeness and approval context.
5. Readiness recommendation is not the same as future submission state.
