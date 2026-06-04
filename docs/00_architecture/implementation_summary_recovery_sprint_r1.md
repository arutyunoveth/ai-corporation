# Implementation Summary Recovery Sprint R1

## Reused Foundation

- Sprint 1 foundation: `deal_registry`, `event_log`, `document_store`, `status_engine`
- Sprint 2A drift logic reused internally:
  - `tender_intake` for deal creation/reuse and source linking
  - `document_ingestion` for canonical document-set context
  - legacy `tender_summary` kept intact as helper contour
- Existing supplier-style CRUD patterns reused for canonical customer registry shape

## Implemented Canonical Modules

- `M-005` Customer Registry
- `M-007` Tender Import
- `M-008` Tender Normalization
- `M-010` Intake Summary / Prioritization
- `M-012` Requirement Extraction

## Assumptions / Detected Mismatches

1. Existing drift `tender_summary` previously occupied `M-012` semantics in code/docs; Recovery R1 restores canonical `M-012` without destructive rename.
2. Canonical `M-007` and `M-008` are separated even though downstream runtime still materializes legacy intake records internally for stability.
3. `source_type` in canonical import remains permissive string-based to support `EIS/ETP/API/MANUAL` without new governance drift.

## Migrations

- `060_create_customer_registry`
- `061_create_tender_import`
- `062_create_tender_normalization`
- `063_create_intake_priority`
- `064_create_requirement_extraction`

## Endpoints

- `POST /customers`
- `GET /customers/{customer_id}`
- `GET /customers`
- `PATCH /customers/{customer_id}`
- `POST /tender-import/runs`
- `GET /tender-import/runs/{tender_import_run_id}`
- `GET /tender-import/events`
- `GET /tender-import/events/{tender_import_event_id}`
- `POST /tender-normalization/build`
- `GET /tender-normalization/{tender_normalization_set_id}`
- `GET /tender-normalization`
- `GET /tender-normalization/records/{tender_normalization_id}`
- `POST /intake-priority/build`
- `GET /intake-priority/{intake_priority_set_id}`
- `GET /intake-priority`
- `GET /intake-priority/records/{intake_priority_id}`
- `POST /requirements/extract`
- `GET /requirements/{requirement_extraction_set_id}`
- `GET /requirements`
- `GET /requirements/records/{requirement_extraction_id}`

## Tests Added

- customer create/read/update/query
- tender import run/event/payload persistence
- tender normalization build and append-only rerun
- intake priority build and factor persistence
- requirement extraction build, source-link persistence, and rerun behavior

## Governance Result

- `M-005`, `M-007`, `M-008`, `M-010`, `M-012` are now explicitly covered as canonical modules.
- Legacy helper contours remain available, but are no longer presented as replacement canon.
