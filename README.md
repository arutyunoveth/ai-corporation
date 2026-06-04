# ai-corporation

Sprint 1 foundation, Sprint 2A intake foundation, Sprint 2B analysis foundation, Sprint 3A supplier-side foundation, Sprint 3B supplier quality foundation, Sprint 4A economics foundation, Sprint 4B risk + approval foundation, Sprint 5A bid-prep foundation, Sprint 5B submission foundation, Sprint 6A execution and delivery foundation, Sprint 6B closure / incident / KPI foundation, Sprint 7A operational intelligence foundation, Sprint 7B orchestration / optimization foundation, Sprint 8A connectors / workspace / controlled-action foundation, Sprint 8B richer integrations / operator session / gated execution foundation, and Sprint 9A vendor execution gateway foundation for the AI Corporation tender business platform. The current repository implements:

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
- `M-029` Bid Document Collector
- `M-030` Bid Package Builder
- `M-031` Bid Completeness Checker
- `M-032` Submission Readiness Gate
- `M-033` Submission Control
- `M-035` Submission Receipt Registry
- `M-036` Post-Submission Tracker
- `M-037` Outcome Intake
- `M-039` Delivery Launch Control
- `M-040` Execution Command Center
- `M-041` Delivery Milestone Tracker
- `M-042` Supplier Fulfillment Tracker
- `M-043` Shipping & Acceptance Tracker
- `M-044` Payment Collection Tracker
- `M-045` Incident & Escalation Desk
- `M-046` Deal Closure & Archive
- `M-047` KPI & Learning Loop
- `M-048` Operational Dashboard Backbone
- `M-049` Archive Export & Handover
- `M-050` Learning Automation Engine
- `M-051` Workflow Orchestration Backbone
- `M-052` Optimization Recommendation Engine
- `M-053` Operator Copilot Feed
- `M-054` Connector Registry & Sync Backbone
- `M-055` Operator Workspace Feed API
- `M-056` Controlled Action Queue
- `M-057` Integration Task Adapter Layer
- `M-058` Operator Session Workspace
- `M-059` Gated Action Execution Ledger
- `M-060` Vendor Connector Profiles
- `M-061` Operator Action Console Backbone
- `M-062` External Execution Gateway Ledger

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
- persisted bid document collections, bid packages, completeness checks, and submission readiness gates
- persisted submission execution sets, attempts, receipts, post-submission trackers, and explicit outcomes
- persisted delivery launch controls, execution command centers, milestones, fulfillment, shipping/acceptance, and payment collection records
- persisted incidents, deal closure/archive snapshots, and KPI/learning outputs
- persisted dashboard snapshots, archive export manifests, and automated learning recommendations
- persisted workflow runs, optimization recommendations, and operator copilot feeds
- persisted connector registries, connector sync runs, workspace feeds, and controlled action queues
- persisted integration tasks, operator sessions, and gated execution ledger runs/results
- persisted vendor connector profiles, operator action console snapshots, and external execution gateway calls/results
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
  - `BDCS-YYYY-NNNNNN`
  - `BPS-YYYY-NNNNNN`
  - `BP-YYYY-NNNNNN`
  - `BCS-YYYY-NNNNNN`
  - `BC-YYYY-NNNNNN`
  - `SRS-YYYY-NNNNNN`
  - `SR-YYYY-NNNNNN`
  - `SES-YYYY-NNNNNN`
  - `SE-YYYY-NNNNNN`
  - `SA-YYYY-NNNNNN`
  - `SRSR-YYYY-NNNNNN`
  - `SRR-YYYY-NNNNNN`
  - `PSTS-YYYY-NNNNNN`
  - `PST-YYYY-NNNNNN`
  - `PSE-YYYY-NNNNNN`
  - `OIS-YYYY-NNNNNN`
  - `OI-YYYY-NNNNNN`
  - `DLS-YYYY-NNNNNN`
  - `DLC-YYYY-NNNNNN`
  - `ECS-YYYY-NNNNNN`
  - `EC-YYYY-NNNNNN`
  - `DMS-YYYY-NNNNNN`
  - `DM-YYYY-NNNNNN`
  - `DME-YYYY-NNNNNN`
  - `SFS-YYYY-NNNNNN`
  - `SF-YYYY-NNNNNN`
  - `SFE-YYYY-NNNNNN`
  - `SAS-YYYY-NNNNNN`
  - `SHA-YYYY-NNNNNN`
  - `SAE-YYYY-NNNNNN`
  - `PCS-YYYY-NNNNNN`
  - `PC-YYYY-NNNNNN`
  - `PCE-YYYY-NNNNNN`
  - `INS-YYYY-NNNNNN`
  - `INC-YYYY-NNNNNN`
  - `ESC-YYYY-NNNNNN`
  - `DCS-YYYY-NNNNNN`
  - `DC-YYYY-NNNNNN`
  - `DAS-YYYY-NNNNNN`
  - `KLS-YYYY-NNNNNN`
  - `KLR-YYYY-NNNNNN`
  - `LN-YYYY-NNNNNN`
  - `DSS-YYYY-NNNNNN`
  - `DSH-YYYY-NNNNNN`
  - `AES-YYYY-NNNNNN`
  - `AE-YYYY-NNNNNN`
  - `LAS-YYYY-NNNNNN`
  - `LA-YYYY-NNNNNN`
  - `WRS-YYYY-NNNNNN`
  - `WR-YYYY-NNNNNN`
  - `WS-YYYY-NNNNNN`
  - `ORS-YYYY-NNNNNN`
  - `OR-YYYY-NNNNNN`
  - `CFS-YYYY-NNNNNN`
  - `CF-YYYY-NNNNNN`
  - `CRG-YYYY-NNNNNN`
  - `CRR-YYYY-NNNNNN`
  - `CSR-YYYY-NNNNNN`
  - `WFS-YYYY-NNNNNN`
  - `WF-YYYY-NNNNNN`
  - `AQS-YYYY-NNNNNN`
  - `AQ-YYYY-NNNNNN`
  - `ITS-YYYY-NNNNNN`
  - `IT-YYYY-NNNNNN`
  - `OSS-YYYY-NNNNNN`
  - `OS-YYYY-NNNNNN`
  - `ELS-YYYY-NNNNNN`
  - `EL-YYYY-NNNNNN`
  - `VCS-YYYY-NNNNNN`
  - `VC-YYYY-NNNNNN`
  - `ACS-YYYY-NNNNNN`
  - `AC-YYYY-NNNNNN`
  - `XES-YYYY-NNNNNN`
  - `XE-YYYY-NNNNNN`

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
- `POST /bid-documents/collect`
- `GET /bid-documents/{bid_document_collection_set_id}`
- `GET /bid-documents`
- `GET /bid-documents/rows/{bid_document_collection_set_id}`
- `POST /bid-packages/build`
- `GET /bid-packages/{bid_package_set_id}`
- `GET /bid-packages`
- `GET /bid-packages/records/{bid_package_id}`
- `POST /bid-completeness/check`
- `GET /bid-completeness/{bid_completeness_set_id}`
- `GET /bid-completeness`
- `GET /bid-completeness/records/{bid_completeness_id}`
- `POST /submission-readiness/build`
- `GET /submission-readiness/{submission_readiness_set_id}`
- `GET /submission-readiness`
- `GET /submission-readiness/records/{submission_readiness_id}`
- `POST /submission-control/build`
- `POST /submission-control/start`
- `POST /submission-control/attempts`
- `GET /submission-control/{submission_execution_set_id}`
- `GET /submission-control`
- `GET /submission-control/records/{submission_execution_id}`
- `POST /submission-receipts/register`
- `GET /submission-receipts/{submission_receipt_set_id}`
- `GET /submission-receipts`
- `GET /submission-receipts/records/{submission_receipt_id}`
- `POST /post-submission/build`
- `POST /post-submission/events`
- `GET /post-submission/{post_submission_tracker_set_id}`
- `GET /post-submission`
- `GET /post-submission/records/{post_submission_tracker_id}`
- `POST /outcome-intake/register`
- `GET /outcome-intake/{outcome_intake_set_id}`
- `GET /outcome-intake`
- `GET /outcome-intake/records/{outcome_intake_id}`
- `POST /delivery-launch/build`
- `POST /delivery-launch/launch`
- `GET /delivery-launch/{delivery_launch_set_id}`
- `GET /delivery-launch`
- `GET /delivery-launch/records/{delivery_launch_id}`
- `POST /execution/build`
- `GET /execution/{execution_command_set_id}`
- `GET /execution`
- `GET /execution/records/{execution_command_id}`
- `POST /delivery-milestones/build`
- `POST /delivery-milestones/events`
- `GET /delivery-milestones/{delivery_milestone_set_id}`
- `GET /delivery-milestones`
- `GET /delivery-milestones/records/{delivery_milestone_id}`
- `POST /supplier-fulfillment/build`
- `POST /supplier-fulfillment/events`
- `GET /supplier-fulfillment/{supplier_fulfillment_set_id}`
- `GET /supplier-fulfillment`
- `GET /supplier-fulfillment/records/{supplier_fulfillment_id}`
- `POST /shipping-acceptance/build`
- `POST /shipping-acceptance/events`
- `GET /shipping-acceptance/{shipping_acceptance_set_id}`
- `GET /shipping-acceptance`
- `GET /shipping-acceptance/records/{shipping_acceptance_id}`
- `POST /payment-collection/build`
- `POST /payment-collection/events`
- `GET /payment-collection/{payment_collection_set_id}`
- `GET /payment-collection`
- `GET /payment-collection/records/{payment_collection_id}`
- `POST /incidents/build`
- `POST /incidents/register`
- `POST /incidents/escalate`
- `GET /incidents/{incident_set_id}`
- `GET /incidents`
- `GET /incidents/records/{incident_id}`
- `POST /deal-closure/build`
- `POST /deal-closure/close`
- `GET /deal-closure/{deal_closure_set_id}`
- `GET /deal-closure`
- `GET /deal-closure/records/{deal_closure_id}`
- `POST /kpi-learning/build`
- `GET /kpi-learning/{kpi_learning_set_id}`
- `GET /kpi-learning`
- `GET /kpi-learning/records/{kpi_learning_id}`
- `POST /dashboards/build`
- `GET /dashboards/{dashboard_snapshot_set_id}`
- `GET /dashboards`
- `GET /dashboards/records/{dashboard_snapshot_id}`
- `POST /archive-export/build`
- `GET /archive-export/{archive_export_set_id}`
- `GET /archive-export`
- `GET /archive-export/records/{archive_export_id}`
- `POST /learning-automation/build`
- `GET /learning-automation/{learning_automation_set_id}`
- `GET /learning-automation`
- `GET /learning-automation/records/{learning_automation_id}`
- `POST /workflow-runs/build`
- `GET /workflow-runs/{workflow_run_set_id}`
- `GET /workflow-runs`
- `GET /workflow-runs/records/{workflow_run_id}`
- `POST /optimization/build`
- `GET /optimization/{optimization_recommendation_set_id}`
- `GET /optimization`
- `GET /optimization/records/{optimization_recommendation_id}`
- `POST /copilot-feed/build`
- `GET /copilot-feed/{copilot_feed_set_id}`
- `GET /copilot-feed`
- `GET /copilot-feed/records/{copilot_feed_id}`
- `POST /connectors/build`
- `POST /connectors/sync`
- `GET /connectors/{connector_registry_set_id}`
- `GET /connectors`
- `GET /connectors/records/{connector_registry_id}`
- `POST /workspace-feed/build`
- `GET /workspace-feed/{workspace_feed_set_id}`
- `GET /workspace-feed`
- `GET /workspace-feed/records/{workspace_feed_id}`
- `POST /action-queue/build`
- `POST /action-queue/approve`
- `GET /action-queue/{action_queue_set_id}`
- `GET /action-queue`
- `GET /action-queue/records/{action_queue_id}`
- `POST /integration-tasks/build`
- `GET /integration-tasks/{integration_task_set_id}`
- `GET /integration-tasks`
- `GET /integration-tasks/records/{integration_task_id}`
- `POST /operator-sessions/build`
- `POST /operator-sessions/items/ack`
- `GET /operator-sessions/{operator_session_set_id}`
- `GET /operator-sessions`
- `GET /operator-sessions/records/{operator_session_id}`
- `POST /execution-ledger/build`
- `POST /execution-ledger/start`
- `GET /execution-ledger/{execution_ledger_set_id}`
- `GET /execution-ledger`
- `GET /execution-ledger/records/{execution_ledger_id}`
- `POST /vendor-connectors/build`
- `GET /vendor-connectors/{vendor_connector_set_id}`
- `GET /vendor-connectors`
- `GET /vendor-connectors/records/{vendor_connector_id}`
- `POST /action-console/build`
- `GET /action-console/{action_console_set_id}`
- `GET /action-console`
- `GET /action-console/records/{action_console_id}`
- `POST /external-execution/build`
- `POST /external-execution/start`
- `GET /external-execution/{external_execution_set_id}`
- `GET /external-execution`
- `GET /external-execution/records/{external_execution_id}`

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
- [docs/01_sprints/Sprint_5A_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_5A_Technical_Spec.md)
- [docs/01_sprints/Sprint_5B_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_5B_Technical_Spec.md)
- [docs/01_sprints/Sprint_6A_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_6A_Technical_Spec.md)
- [docs/01_sprints/Sprint_6B_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_6B_Technical_Spec.md)
- [docs/01_sprints/Sprint_7A_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_7A_Technical_Spec.md)
- [docs/01_sprints/Sprint_7B_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_7B_Technical_Spec.md)
- [docs/01_sprints/Sprint_8A_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_8A_Technical_Spec.md)
- [docs/01_sprints/Sprint_8B_Technical_Spec.md](/Users/master/Documents/AI-Corporation/docs/01_sprints/Sprint_8B_Technical_Spec.md)
- [docs/03_entities/Entity_Catalog_Sprint_1.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_1.md)
- [docs/03_entities/Entity_Catalog_Sprint_2.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_2.md)
- [docs/03_entities/Entity_Catalog_Sprint_3A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_3A.md)
- [docs/03_entities/Entity_Catalog_Sprint_3B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_3B.md)
- [docs/03_entities/Entity_Catalog_Sprint_4A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_4A.md)
- [docs/03_entities/Entity_Catalog_Sprint_4B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_4B.md)
- [docs/03_entities/Entity_Catalog_Sprint_5A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_5A.md)
- [docs/03_entities/Entity_Catalog_Sprint_5B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_5B.md)
- [docs/03_entities/Entity_Catalog_Sprint_6A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_6A.md)
- [docs/03_entities/Entity_Catalog_Sprint_6B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_6B.md)
- [docs/03_entities/Entity_Catalog_Sprint_7A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_7A.md)
- [docs/03_entities/Entity_Catalog_Sprint_8A.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_8A.md)
- [docs/03_entities/Entity_Catalog_Sprint_7B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_7B.md)
- [docs/03_entities/Entity_Catalog_Sprint_8B.md](/Users/master/Documents/AI-Corporation/docs/03_entities/Entity_Catalog_Sprint_8B.md)
- [docs/00_architecture/implementation_summary_sprint_2a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_2a.md)
- [docs/00_architecture/implementation_summary_sprint_2b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_2b.md)
- [docs/00_architecture/implementation_summary_sprint_3a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_3a.md)
- [docs/00_architecture/implementation_summary_sprint_3b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_3b.md)
- [docs/00_architecture/implementation_summary_sprint_4a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_4a.md)
- [docs/00_architecture/implementation_summary_sprint_4b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_4b.md)
- [docs/00_architecture/implementation_summary_sprint_5a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_5a.md)
- [docs/00_architecture/implementation_summary_sprint_5b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_5b.md)
- [docs/00_architecture/implementation_summary_sprint_6a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_6a.md)
- [docs/00_architecture/implementation_summary_sprint_6b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_6b.md)
- [docs/00_architecture/implementation_summary_sprint_7a.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_7a.md)
- [docs/00_architecture/implementation_summary_sprint_7b.md](/Users/master/Documents/AI-Corporation/docs/00_architecture/implementation_summary_sprint_7b.md)
