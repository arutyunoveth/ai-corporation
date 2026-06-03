# ai-corporation

Sprint 1 foundation, Sprint 2A intake foundation, Sprint 2B analysis foundation, Sprint 3A supplier-side foundation, Sprint 3B supplier quality foundation, Sprint 4A economics foundation, and Sprint 4B risk + approval foundation for the AI Corporation tender business platform. The current repository implements:

- `M-001` Deal Registry
- `M-002` Status Model Engine
- `M-003` Document Store
- `M-004` Event Log & Decision Journal
- `M-008` Tender Intake Pipeline
- `M-011` Document Ingestion Layer
- `M-012` Tender Summary Builder
- `M-009` Tender Screening Engine
- `M-010` Priority Scoring Engine
- `M-013` Compliance Matrix Builder
- `M-014` Document Requirement Extractor
- `M-015` Initial Tech Risk Flags
- `M-006` Supplier Registry
- `M-016` Supplier Search
- `M-017` RFQ Generator
- `M-018` Supplier Communication Tracker
- `M-019` TKP Repository
- `M-020` Supplier Verification
- `M-021` Quote Comparison Engine
- `M-022` Cost Model Engine
- `M-023` Cash Gap Calculator
- `M-024` Financing Strategy Engine
- `M-025` Finance Memo Builder
- `M-026` Contract Risk Parser
- `M-027` Integrated Risk Memo Builder
- `M-028` CEO Approval Cockpit

The implementation follows the source-of-truth documents committed under `docs/`.

## Current Scope

- canonical deal records with `deal_id`
- formal status transitions and append-only history
- artifact storage metadata with versioning and links
- append-only event and decision journals
- tender intake records and normalized source payload snapshots
- formal document sets and ingestion runs
- persisted tender summaries with source lineage
- persisted screening, priority scoring, compliance matrix, document requirement, and initial tech risk records
- persisted supplier profiles, shortlists, RFQ batches, communication threads, and quotes
- persisted supplier verification runs, comparison rows, and recommendations
- persisted cost model, cash gap, financing strategy, and finance memo records
- persisted contract risks, integrated risk memos, and CEO approval decisions
- FastAPI endpoints, Alembic migrations, seed data, and integration tests

## Implementation Summary

- Stack: `FastAPI + SQLAlchemy 2 + Alembic + Pydantic + pytest`
- Runtime target: PostgreSQL
- Test runtime: SQLite in-memory for fast integration coverage
- Default status on create: `NEW`
- Business IDs are generated in application code with DB uniqueness guarantees and retry-friendly formatting:
  - `DL-YYYY-NNNNNN`
  - `ART-YYYY-NNNNNN`
  - `EVT-YYYY-NNNNNN`
  - `DEC-YYYY-NNNNNN`
  - `INT-YYYY-NNNNNN`
  - `DS-YYYY-NNNNNN`
  - `DIR-YYYY-NNNNNN`
  - `TS-YYYY-NNNNNN`
  - `SCR-YYYY-NNNNNN`
  - `PRS-YYYY-NNNNNN`
  - `CM-YYYY-NNNNNN`
  - `DRS-YYYY-NNNNNN`
  - `IRF-YYYY-NNNNNN`
  - `SUP-YYYY-NNNNNN`
  - `SSL-YYYY-NNNNNN`
  - `RB-YYYY-NNNNNN`
  - `RFQ-YYYY-NNNNNN`
  - `SCS-YYYY-NNNNNN`
  - `SCT-YYYY-NNNNNN`
  - `SM-YYYY-NNNNNN`
  - `QS-YYYY-NNNNNN`
  - `Q-YYYY-NNNNNN`
  - `SVS-YYYY-NNNNNN`
  - `SV-YYYY-NNNNNN`
  - `QCS-YYYY-NNNNNN`
  - `CMS-YYYY-NNNNNN`
  - `CMD-YYYY-NNNNNN`
  - `CGS-YYYY-NNNNNN`
  - `CG-YYYY-NNNNNN`
  - `FSS-YYYY-NNNNNN`
  - `FS-YYYY-NNNNNN`
  - `FMS-YYYY-NNNNNN`
  - `FM-YYYY-NNNNNN`
  - `CRS-YYYY-NNNNNN`
  - `CR-YYYY-NNNNNN`
  - `IRMS-YYYY-NNNNNN`
  - `IRM-YYYY-NNNNNN`
  - `CAS-YYYY-NNNNNN`
  - `CA-YYYY-NNNNNN`

## Repository Layout

```text
docs/
  00_architecture/
  01_sprints/
  02_modules/
  03_entities/
src/
  modules/
  shared/
migrations/
tests/
```

## Local Run

1. Create a virtual environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

2. Start PostgreSQL:

```bash
docker compose up -d
```

3. Export the database URL:

```bash
export AI_CORP_DATABASE_URL=postgresql+psycopg://ai_corporation:ai_corporation@localhost:5432/ai_corporation
```

4. Apply migrations:

```bash
alembic upgrade head
```

5. Run the API:

```bash
uvicorn src.main:app --reload
```

## Tests

```bash
pytest
```

## Implemented Endpoints

- `POST /deals`
- `GET /deals`
- `GET /deals/{deal_id}`
- `PATCH /deals/{deal_id}`
- `POST /status/validate-transition`
- `POST /status/apply-transition`
- `GET /status/history/{deal_id}`
- `POST /artifacts`
- `POST /artifacts/{artifact_ref}/versions`
- `GET /artifacts/{artifact_ref}`
- `GET /artifacts/{artifact_ref}/versions`
- `POST /artifacts/{artifact_ref}/links`
- `POST /events`
- `POST /decisions`
- `GET /events`
- `GET /decisions`
- `POST /intake/tenders`
- `GET /intake/tenders/{intake_id}`
- `GET /intake/tenders`
- `POST /document-ingestion/sets`
- `GET /document-ingestion/sets/{document_set_id}`
- `GET /document-ingestion/sets`
- `POST /document-ingestion/sets/{document_set_id}/runs`
- `POST /tender-summaries`
- `GET /tender-summaries/{tender_summary_id}`
- `GET /tender-summaries`
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
- `POST /supplier-verification/build`
- `GET /supplier-verification/{supplier_verification_set_id}`
- `GET /supplier-verification`
- `GET /supplier-verification/records/{supplier_verification_id}`
- `POST /quote-comparison/build`
- `GET /quote-comparison/{quote_comparison_set_id}`
- `GET /quote-comparison`
- `GET /quote-comparison/recommendation/{quote_comparison_set_id}`
- `POST /cost-model/build`
- `GET /cost-model/{cost_model_set_id}`
- `GET /cost-model`
- `GET /cost-model/records/{cost_model_id}`
- `POST /cash-gap/build`
- `GET /cash-gap/{cash_gap_set_id}`
- `GET /cash-gap`
- `GET /cash-gap/records/{cash_gap_id}`
- `POST /financing-strategy/build`
- `GET /financing-strategy/{financing_strategy_set_id}`
- `GET /financing-strategy`
- `GET /financing-strategy/records/{financing_strategy_id}`
- `POST /finance-memo/build`
- `GET /finance-memo/{finance_memo_set_id}`
- `GET /finance-memo`
- `GET /finance-memo/records/{finance_memo_id}`
- `POST /contract-risks/build`
- `GET /contract-risks/{contract_risk_set_id}`
- `GET /contract-risks`
- `GET /contract-risks/records/{contract_risk_id}`
- `POST /integrated-risk-memo/build`
- `GET /integrated-risk-memo/{integrated_risk_memo_set_id}`
- `GET /integrated-risk-memo`
- `GET /integrated-risk-memo/records/{integrated_risk_memo_id}`
- `POST /ceo-approval/build`
- `POST /ceo-approval/decide`
- `GET /ceo-approval/{ceo_approval_set_id}`
- `GET /ceo-approval`
- `GET /ceo-approval/records/{ceo_approval_id}`

## Source Of Truth

- [docs/00_architecture/Unified_Module_Registry.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/Unified_Module_Registry.md)
- [docs/00_architecture/Module_Dependency_Map_and_MVP_Core.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/Module_Dependency_Map_and_MVP_Core.md)
- [docs/01_sprints/MVP_First_Wave_Roadmap_and_High_Level_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/MVP_First_Wave_Roadmap_and_High_Level_Spec.md)
- [docs/01_sprints/MVP_First_Wave_Backlog.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/MVP_First_Wave_Backlog.md)
- [docs/01_sprints/Sprint_1_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_1_Technical_Spec.md)
- [docs/01_sprints/Sprint_2_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_2_Technical_Spec.md)
- [docs/01_sprints/Sprint_3A_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_3A_Technical_Spec.md)
- [docs/01_sprints/Sprint_3B_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_3B_Technical_Spec.md)
- [docs/01_sprints/Sprint_4A_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_4A_Technical_Spec.md)
- [docs/01_sprints/Sprint_4B_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_4B_Technical_Spec.md)
- [docs/03_entities/Entity_Catalog_Sprint_1.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_1.md)
- [docs/03_entities/Entity_Catalog_Sprint_2.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_2.md)
- [docs/03_entities/Entity_Catalog_Sprint_3A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_3A.md)
- [docs/03_entities/Entity_Catalog_Sprint_3B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_3B.md)
- [docs/03_entities/Entity_Catalog_Sprint_4A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_4A.md)
- [docs/03_entities/Entity_Catalog_Sprint_4B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_4B.md)
- [docs/00_architecture/implementation_summary_sprint_2a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_2a.md)
- [docs/00_architecture/implementation_summary_sprint_2b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_2b.md)
- [docs/00_architecture/implementation_summary_sprint_3a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_3a.md)
- [docs/00_architecture/implementation_summary_sprint_3b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_3b.md)
- [docs/00_architecture/implementation_summary_sprint_4a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_4a.md)
- [docs/00_architecture/implementation_summary_sprint_4b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_4b.md)
