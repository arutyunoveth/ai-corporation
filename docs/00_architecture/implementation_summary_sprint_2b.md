# Sprint 2B Implementation Summary

## Reused Foundation

- `M-001` canonical `deal` registry and external refs
- `M-002` status model engine and append-only status history
- `M-003` artifact backbone with `artifact_ref`
- `M-004` append-only event journal
- Sprint 2A intake package spine:
  - `tender_intake_records`
  - `document_sets`
  - `tender_summaries`
- shared application-level business ID generation pattern `PREFIX-YYYY-NNNNNN`
- modular `FastAPI + SQLAlchemy 2 + Alembic + Pydantic + pytest` structure

## Detected Mismatches

1. Legacy module cards for `M-009`, `M-010`, `M-013`, `M-014`, and `M-015` reference older intermediate objects such as `normalization_id`, `screening_memo_id`, `intake_summary_id`, and `bid_document_requirement_set_id`.
2. The current repository already formalizes the Sprint 2A intake package around `deal_id + intake_id + document_set_id + tender_summary_id`, so Sprint 2B extends that spine instead of recreating the older lineage.
3. Existing status contracts are stable in Sprint 1. Sprint 2B therefore stores analytical outcomes and `recommended_next_status` without silently mutating the canonical deal lifecycle.

## Assumptions

1. Sprint 2B is intentionally rule-based and transparent. No LLM dependency or probabilistic extraction layer is introduced in this iteration.
2. Analytical outputs are append-only persisted records. Reruns create new records instead of overwriting prior results.
3. `deal_id` is mandatory for every analytical record. `intake_id`, `document_set_id`, and `tender_summary_id` are treated as the minimum intake-package prerequisites.
4. `compliance_matrix` and `document_requirement_set` are the upstream formal objects for initial tech risk construction in this sprint.

## Exact Sprint 2B Scope

- `M-009` Tender Screening Engine
- `M-010` Priority Scoring Engine
- `M-013` Compliance Matrix Builder
- `M-014` Document Requirement Extractor
- `M-015` Initial Tech Risk Flags

Sprint 2B output is a persisted formal analysis package built on top of the existing intake package:

- `tender_screening_records`
- `priority_score_records`
- `compliance_matrices`
- `compliance_matrix_rows`
- `document_requirement_sets`
- `document_requirement_rows`
- `initial_tech_risk_flag_sets`
- `initial_tech_risk_flags`

## Added Business IDs

- `SCR-YYYY-NNNNNN` for screening records
- `PRS-YYYY-NNNNNN` for priority score records
- `CM-YYYY-NNNNNN` for compliance matrices
- `DRS-YYYY-NNNNNN` for document requirement sets
- `IRF-YYYY-NNNNNN` for initial tech risk flag sets

## Added Migrations

1. `009_create_tender_screening.py`
2. `010_create_priority_scoring.py`
3. `011_create_compliance_matrix.py`
4. `012_create_document_requirements.py`
5. `013_create_initial_tech_risks.py`

## Added Endpoints

- `POST /screening/run`
- `GET /screening/{screening_id}`
- `GET /screening`
- `POST /priority-scoring/run`
- `GET /priority-scoring/{priority_score_id}`
- `GET /priority-scoring`
- `POST /compliance-matrix/build`
- `GET /compliance-matrix/{compliance_matrix_id}`
- `GET /compliance-matrix`
- `POST /document-requirements/extract`
- `GET /document-requirements/{document_requirement_set_id}`
- `GET /document-requirements`
- `POST /initial-tech-risks/build`
- `GET /initial-tech-risks/{risk_flag_set_id}`
- `GET /initial-tech-risks`

## Added Tests

- screening pass / fail / needs-review paths
- persisted priority score and priority bucket
- persisted compliance matrix rows
- persisted document requirement rows
- persisted initial tech risk flags with severity and category
- linkage of all Sprint 2B records back to `deal_id`
- event-log trace coverage for core analytical steps
- query-by-deal coverage
- prerequisite failure path
- rerun behavior as append-only analytical history

## Known Limitations

1. Screening, scoring, matrix, requirement extraction, and risk detection are intentionally heuristic and deterministic.
2. No lifecycle auto-transition is performed from analytical outcomes in this sprint.
3. Source trace is persisted as lightweight object refs and pointers, not as a full excerpt-level provenance graph.
4. Business ID generation remains lookup-based and is not refactored into a separate sequencing subsystem.

## TODO For Next Step

1. Feed Sprint 2B outputs into supplier-side shortlist and RFQ planning.
2. Enrich compliance and requirement extraction from document content, not only summary and document-set metadata.
3. Add more explicit orchestration hooks for downstream finance and integrated risk modules.
4. Introduce configurable scoring and screening thresholds via governance modules instead of inline rule constants.
