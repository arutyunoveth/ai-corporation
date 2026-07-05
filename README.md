# ai-corporation

Canonical business registry is locked to `M-001..M-055`.

This repository currently contains:

- canonical modules that match the locked registry
- bounded-implemented late canonical slots for `M-049/M-050` limited to internal metadata/control
- deferred platform/governance late slots for `M-052..M-055`
- useful internal/platform extensions that drifted beyond the locked canonical range

The repository now includes the reconciliation layer plus Recovery Sprints R1, R2, R3, R4, and R5, so canonical coverage has been restored for `M-005`, `M-007`, `M-008`, `M-010`, `M-012`, and the full recovery bands `M-031..M-048` without destructive refactor.

The project is now in a separate launch-readiness phase. Recovery is closed, but launch approval still depends on honest handling of deferred late slots and operational compensating controls.

## Current Product Status

- Runtime Metadata Phase `I1` is complete for the bounded internal metadata-control slice around `M-049`, `M-050`, the runtime control trace ledger, and metadata slice integration.
- Commercial MVP v1 is complete at the repository package level.
- Controlled Commercial Pilot Stage is complete at the repository package level.
- Design-Partner Pilot Stage is complete at the repository package level.
- Restricted Paid Pilot Operations Setup (PP0) is complete: operations runbook, local data handling policy, templates, and first-pilot checklist are in place.
- Real Partner Tender Folder Runner (PP1) is complete: a local folder-based CLI command that validates folder structure, creates intake records, runs analysis, applies the export guard, and writes partner-facing outputs.
- Tender Operator Pilot Runner Refinement (PP1R) is complete: RFQ-first workflow for tender/operator companies with calibrated contract risk, supplier questions, RFQ draft, TKP comparison/economics, and bid decision recommendation.
- Current product recommendation: `GO to restricted paid pilot with manual-control boundaries`.
- A pilot access boundary, partner workspace, redaction workflow, report export package, feedback/outcome loop, and end-to-end dry run are all present.
- Full `pytest` currently passes in local verification.
- Deterministic commercial pre-bid demo reporting is now available for internal/customer walkthroughs.
- Supplier Profile Relevance Scoring is now available in the Tender Operator Agent Demo: deterministic rule-based scoring of 44-ФЗ search results and document text against a configurable supplier profile, with a UI panel for profile management.
- Controlled LLM pre-bid analysis is available only in bounded, schema-validated, traceable, human-reviewed mode.
- A minimal internal commercial operator console is available for dashboard/report/requirements/risk/trace review and controlled internal actions.
- A commercial workspace now links manual TKP registration, deterministic economics, and bid-readiness checks into an internal-only reportable flow.
- A dedicated Tender Operator Agent demo page is available at `/demo/tender-agent` with three controlled modes: procurement search/intake, local Upload & Analyze, and a synthetic walkthrough.
- Tender Operator Agent demo now separates procurement search from documentation intake: offline-safe procurement discovery (`demo_local`), public HTML fallback for ЕИС search, read-only `getDocsIP` intake for an individual-person token, local document intake, XLSX supplier-quote normalization, quote comparison, agent work journal, HTML report, and demo-mode economics estimation without external actions.
- Public 44-ФЗ search to live getDocsIP flow: keyword search on zakupki.gov.ru, lightweight HTML parser extracts cards, one-click handoff to getDocsIP archive download, safe extraction, analysis, and report — all without login or captcha bypass.
- Controlled pilot scenario pack, operator workflow hardening, evidence ledger, sales materials, and dry-run harness are all present.
- No broad autonomy is open.
- No external execution is open.
- No procurement platform submission, EDS/signature work, or supplier email automation is implemented.

## Product Docs

- [docs/product/README.md](docs/product/README.md)
- [docs/product/Product_Master_Plan_v2.md](docs/product/Product_Master_Plan_v2.md)
- [docs/product/Commercial_MVP_v1_Roadmap.md](docs/product/Commercial_MVP_v1_Roadmap.md)
- [docs/product/TKP_Economics_Bid_Readiness.md](docs/product/TKP_Economics_Bid_Readiness.md)
- [docs/product/MVP_v1_Final_Audit.md](docs/product/MVP_v1_Final_Audit.md)
- [docs/product/Pilot_Playbook_MVP_v1.md](docs/product/Pilot_Playbook_MVP_v1.md)
- [docs/product/Controlled_Pilot_Final_Audit.md](docs/product/Controlled_Pilot_Final_Audit.md)
- [docs/product/Controlled_Pilot_GO_NO_GO_Decision.md](docs/product/Controlled_Pilot_GO_NO_GO_Decision.md)
- [docs/product/Post_Pilot_Roadmap_Revision.md](docs/product/Post_Pilot_Roadmap_Revision.md)
- [docs/product/MVP_v1_Scope.md](docs/product/MVP_v1_Scope.md)
- [docs/product/MVP_v1_Non_Goals.md](docs/product/MVP_v1_Non_Goals.md)
- [docs/product/Human_Control_Policy_v2.md](docs/product/Human_Control_Policy_v2.md)
- [docs/product/Product_Backlog.md](docs/product/Product_Backlog.md)
- [docs/product/Repository_Public_Readiness_Check.md](docs/product/Repository_Public_Readiness_Check.md)
- [docs/product/Restricted_Paid_Pilot_Operations_Runbook.md](docs/product/Restricted_Paid_Pilot_Operations_Runbook.md)
- [docs/product/Local_Pilot_Data_Handling_Policy.md](docs/product/Local_Pilot_Data_Handling_Policy.md)
- [docs/product/First_Restricted_Pilot_Checklist.md](docs/product/First_Restricted_Pilot_Checklist.md)
- [docs/product/Run_Partner_Tender_Folder.md](docs/product/Run_Partner_Tender_Folder.md)
- [docs/product/Tender_Operator_Pilot_Runbook.md](docs/product/Tender_Operator_Pilot_Runbook.md)
- [docs/product/Tender_Operator_Site_Deployment.md](docs/product/Tender_Operator_Site_Deployment.md)
- [docs/product/Calibrated_Contract_Risk_Method.md](docs/product/Calibrated_Contract_Risk_Method.md)
- [docs/product/Tender_Operator_RFQ_Workflow.md](docs/product/Tender_Operator_RFQ_Workflow.md)
- [docs/demo/tender_rag_analysis/README.md](docs/demo/tender_rag_analysis/README.md) — Demo runbook for tender RAG analysis

## Unified Site + Pilot Preview

To preview the Arvectum site with the live Tender Operator pilot behind one
entrypoint:

```bash
docker compose -f docker-compose.site-pilot.yml up --build
```

Open:

- `http://127.0.0.1:8081/`
- `http://127.0.0.1:8081/cases/tender-operator-demo.html`
- `http://127.0.0.1:8081/pilot/tender-agent`

For a pure Python same-port preview without Nginx:

```bash
AI_CORP_SITE_PUBLIC_ROOT=./arvectum-landing/public \
./.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8090
```

Then open:

- `http://127.0.0.1:8090/cases/tender-operator-demo.html`
- `http://127.0.0.1:8090/pilot/tender-agent`
## Customer Demo Package

- [docs/demo/customer_demo_script_7min.md](docs/demo/customer_demo_script_7min.md) — 7-minute demo script with presenter cues
- [docs/demo/customer_one_pager.md](docs/demo/customer_one_pager.md) — one-pager for the customer
- [docs/demo/pilot_scope.md](docs/demo/pilot_scope.md) — pilot scope, metrics, and success criteria
- [docs/demo/security_and_limits_faq.md](docs/demo/security_and_limits_faq.md) — honest FAQ for customer security questions
- [docs/demo/demo_runbook.md](docs/demo/demo_runbook.md) — pre-meeting runbook with checks and fallbacks
- [docs/product/tender_agent_demo_acceptance_checklist.md](docs/product/tender_agent_demo_acceptance_checklist.md) — internal acceptance checklist

- [docs/demo_tender_operator_agent.md](docs/demo_tender_operator_agent.md)
- [docs/product/tender_app_reuse_audit.md](docs/product/tender_app_reuse_audit.md)
- [docs/product/zakupki_soap_integration.md](docs/product/zakupki_soap_integration.md)
- [docs/product/templates/](docs/product/templates/) — pilot templates directory

## Reconciliation Docs

- [canonical_module_registry_locked.md](docs/99_governance/canonical_module_registry_locked.md)
- [canonical_vs_implemented_mapping.md](docs/99_governance/canonical_vs_implemented_mapping.md)
- [non_canonical_extension_register.md](docs/99_governance/non_canonical_extension_register.md)
- [registry_recovery_plan.md](docs/99_governance/registry_recovery_plan.md)
- [Registry_Reconciliation_R6.md](docs/99_governance/Registry_Reconciliation_R6.md)
- [implementation_summary_recovery_sprint_r1.md](docs/00_architecture/implementation_summary_recovery_sprint_r1.md)
- [implementation_summary_recovery_sprint_r2.md](docs/00_architecture/implementation_summary_recovery_sprint_r2.md)
- [implementation_summary_recovery_sprint_r3.md](docs/00_architecture/implementation_summary_recovery_sprint_r3.md)
- [implementation_summary_recovery_sprint_r4.md](docs/00_architecture/implementation_summary_recovery_sprint_r4.md)
- [implementation_summary_recovery_sprint_r5.md](docs/00_architecture/implementation_summary_recovery_sprint_r5.md)
- [implementation_summary_pre_l1_ops_visibility.md](docs/00_architecture/implementation_summary_pre_l1_ops_visibility.md)
- [Recovery_Sprint_R1_Technical_Spec.md](docs/01_sprints/Recovery_Sprint_R1_Technical_Spec.md)
- [Recovery_Sprint_R2_Technical_Spec.md](docs/01_sprints/Recovery_Sprint_R2_Technical_Spec.md)
- [Recovery_Sprint_R3_Technical_Spec.md](docs/01_sprints/Recovery_Sprint_R3_Technical_Spec.md)
- [Recovery_Sprint_R4_Technical_Spec.md](docs/01_sprints/Recovery_Sprint_R4_Technical_Spec.md)
- [Recovery_Sprint_R5_Technical_Spec.md](docs/01_sprints/Recovery_Sprint_R5_Technical_Spec.md)
- [Entity_Catalog_Recovery_Sprint_R1.md](docs/03_entities/Entity_Catalog_Recovery_Sprint_R1.md)
- [Entity_Catalog_Recovery_Sprint_R2.md](docs/03_entities/Entity_Catalog_Recovery_Sprint_R2.md)
- [Entity_Catalog_Recovery_Sprint_R3.md](docs/03_entities/Entity_Catalog_Recovery_Sprint_R3.md)
- [Entity_Catalog_Recovery_Sprint_R4.md](docs/03_entities/Entity_Catalog_Recovery_Sprint_R4.md)
- [Entity_Catalog_Recovery_Sprint_R5.md](docs/03_entities/Entity_Catalog_Recovery_Sprint_R5.md)
- [Final_Recovery_Audit.md](docs/99_governance/Final_Recovery_Audit.md)
- [Launch_Readiness_Gap_Audit.md](docs/10_launch/Launch_Readiness_Gap_Audit.md)
- [Launch_L1_Minimum_Baseline.md](docs/10_launch/Launch_L1_Minimum_Baseline.md)
- [Deferred_Modules_Risk_Assessment.md](docs/10_launch/Deferred_Modules_Risk_Assessment.md)
- [Launch_L1_Go_NoGo_Checklist.md](docs/10_launch/Launch_L1_Go_NoGo_Checklist.md)
- [Launch_L1_Restrictions.md](docs/10_launch/Launch_L1_Restrictions.md)
- [Launch_L1_Operator_Runbook.md](docs/10_launch/Launch_L1_Operator_Runbook.md)
- [Launch_L1_Execution_Checklist.md](docs/10_launch/Launch_L1_Execution_Checklist.md)
- [Launch_L1_Pilot_Playbook.md](docs/10_launch/Launch_L1_Pilot_Playbook.md)
- [Launch_L1_Control_Gates.md](docs/10_launch/Launch_L1_Control_Gates.md)
- [Pre_L1_Ops_Visibility_Package.md](docs/10_launch/Pre_L1_Ops_Visibility_Package.md)
- [Pre_L1_Attention_and_Red_Flags.md](docs/10_launch/Pre_L1_Attention_and_Red_Flags.md)
- [Pre_L1_Owner_Overview.md](docs/10_launch/Pre_L1_Owner_Overview.md)
- [Repository_Sync_Integrity_Report.md](docs/10_launch/Repository_Sync_Integrity_Report.md)
- [Dry_Run_0_Entry_Criteria.md](docs/10_launch/Dry_Run_0_Entry_Criteria.md)
- [Dry_Run_0_Scenario.md](docs/10_launch/Dry_Run_0_Scenario.md)
- [Dry_Run_0_Execution_Log_Template.md](docs/10_launch/Dry_Run_0_Execution_Log_Template.md)
- [Dry_Run_0_Review_Template.md](docs/10_launch/Dry_Run_0_Review_Template.md)
- [Dry_Run_0_Success_Criteria.md](docs/10_launch/Dry_Run_0_Success_Criteria.md)
- [Repository_Public_State_Checklist.md](docs/10_launch/Repository_Public_State_Checklist.md)
- [mvp_runtime_phase_1_final_review.md](docs/10_launch/mvp_runtime_phase_1_final_review.md)
- [mvp_runtime_phase_1_exit_decision.md](docs/10_launch/mvp_runtime_phase_1_exit_decision.md)
- [mvp_runtime_phase_1_post_phase_recommendations.md](docs/10_launch/mvp_runtime_phase_1_post_phase_recommendations.md)

## Governance Status

### Canonical Modules Implemented Exactly

- `M-001`, `M-002`, `M-003`, `M-004`
- `M-005`
- `M-006`
- `M-007`, `M-008`
- `M-009`
- `M-010`
- `M-011`
- `M-012`
- `M-013` through `M-030`
- `M-031` through `M-048`
- `M-051`

### Bounded Runtime Canonical Modules

- `M-049`
- `M-050`

These canonical slots now have a bounded internal metadata/control implementation only. Broad agent execution, prompt execution, autonomous behavior, and runtime expansion beyond the approved slice remain intentionally deferred.

### Reconciled Non-Runtime Canonical Slots

- `M-052` Notification Layer -> `PLATFORM_ONLY`
- `M-053` Red Flag Registry -> `GOVERNANCE_ONLY`
- `M-054` Master Dashboard -> `PLATFORM_ONLY`
- `M-055` SaaS Productization Tracker -> `GOVERNANCE_ONLY`

These locked-registry slots are now reconciled explicitly. They do not require standalone runtime endpoints/models before Launch Sprint `L1`.

### Non-Canonical / Internal Extensions

- `M-056` Controlled Action Queue
- `M-057` Integration Task Adapter Layer
- `M-058` Operator Session Workspace
- `M-059` Gated Action Execution Ledger
- `M-060` Vendor Connector Profiles
- `M-061` Operator Action Console Backbone
- `M-062` External Execution Gateway Ledger

These extensions remain useful, but they are not part of the locked canonical business registry.

### Recovery R6 Notes

- Helper/internal compatibility contours still present:
  - `incidents`
  - `deal_closure`
  - `kpi_learning`
  - `archive_export`
  - `dashboard_snapshots`
  - `submission_*`
  - `delivery_launch`
  - `execution_command`
  - `delivery_milestones`
  - `supplier_fulfillment`
  - `shipping_acceptance`
  - `payment_collection`
- Known ID prefix overlaps:
  - `SAS` -> canonical `submission_archive_set_id`, helper `shipping_acceptance_set_id`
  - `SCS` -> helper `supplier_communication_set_id`, canonical `supplier_contract_set_id`
  - `ACS` -> canonical `acceptance_control_set_id`, non-canonical `action_console_set_id`
- Registry reconciliation is now complete for `M-052..M-055`; no unresolved locked-registry mismatches remain.
- AI/LLM, prompt, agent, and external platform execution work remain intentionally deferred.
- Before Launch Sprint `L1`, the remaining governance gate is to keep reserved `M-049/M-050` closed until a dedicated post-launch AI/runtime phase is approved.
- Launch readiness is audited separately from recovery completion; the current decision is `GO with restrictions` for a controlled operator-assisted pilot, not for unattended or autonomous launch.
- Launch Sprint `L1` is therefore allowed only as a controlled pilot with a runbook, checklist, pilot playbook, and mandatory human control gates.
- A pre-L1 ops visibility mini-gap closure now adds an internal `launch_visibility` helper for pilot attention aggregation and owner/operator overview without reopening `M-049/M-050` or reclassifying `M-052..M-055`.
- Dry Run 0 has now been executed and reviewed.
- The immediate next repository gate is no longer Dry Run 0.
- The current recommendation is `GO with minor fixes before L1`, not direct uncontrolled pilot execution.
- Controlled Pilot L1 is now formally staged under a locked master plan and S1 setup package.
- Controlled Pilot L1 Deal #1 has now been executed with explicit review output.
- Controlled Pilot L1 Deal #2 has now been executed as a confirmation wave.
- Controlled Pilot L1 block completed.
- Final phase decision: `GO with restrictions`.
- Recommended next step: `broader internal usage under the same controlled restrictions`.
- Broader Internal Usage is now formally staged under a locked master plan and S1 setup package.
- Broader Internal Usage Wave #1 has now been executed with explicit review output.
- Broader Internal Usage Wave #2 has now been executed as a stability check.
- Broader Internal Usage block completed.
- Final phase decision: `GO to broader internal steady-state usage`.
- Recommended next step: `continue broader internal steady-state usage under the same controlled restrictions`.
- Broader Internal Steady-State Usage is now formally staged under a locked master plan and S1 setup package.
- Steady-State Operational Cycle #1 has now been executed with explicit review output.
- Steady-State Operational Cycle #2 has now been executed as a load and cadence check.
- Broader Internal Steady-State Usage block completed.
- Final phase decision: `Continue internal steady-state usage`.
- Recommended next step: `continue internal steady-state usage under the same controlled restrictions while keeping future runtime planning explicitly separate`.
- Internal Steady-State Optimization is now formally staged under a locked master plan and S1 baseline setup package.
- Optimization Cycle #1 has now been executed with explicit review output.
- Optimization Cycle #2 has now been executed as a repeatability check.
- Internal Steady-State Optimization block completed.
- Final phase decision: `Continue optimized internal usage`.
- Recommended next step: `continue optimized internal usage under the same controlled restrictions while keeping separate runtime planning as an explicit later decision`.
- Deferred Runtime Planning is now formally staged under a locked master plan and S1 scope/constraints package.
- M-049/M-050 readiness architecture is now formally documented.
- M-052..M-055 activation boundaries are now formally documented.
- Deferred Runtime Planning block completed.
- Final phase decision: `Open limited runtime design phase`.
- Recommended next step: `open a separate limited runtime design phase with explicit boundaries, without opening runtime implementation yet`.
- Limited Runtime Design is now formally staged under a locked master plan and S1 scope/safety package.
- Current phase status: `repository ready for limited runtime design work`.
- M-049/M-050 limited runtime design is now formally documented.
- M-052..M-055 supporting runtime design is now formally documented.
- Limited Runtime Design block completed.
- Final phase decision: `Open limited runtime implementation phase`.
- Recommended next step: `open a separately approved limited runtime implementation phase with explicit boundaries, without broad runtime claims or autonomous positioning`.
- Limited Runtime Implementation Gate is now formally staged under a locked master plan and S1 scope/safety lock package.
- Current phase status: `repository ready for MVP runtime slice definition`.
- First MVP runtime slice is now formally defined.
- MVP implementation package is now ready for execution planning.
- Limited Runtime Implementation Gate block completed.
- Final phase decision: `GO to MVP runtime implementation`.
- Recommended next step: `open MVP Runtime Implementation — Phase 1 for the bounded internal metadata-control slice for M-049/M-050 only`.
- MVP Runtime Implementation — Phase 1 is now formally staged for the bounded internal metadata-control slice for `M-049/M-050`.
- Current phase status: `repository ready for bounded MVP runtime module implementation`.
- M-049 bounded runtime slice implemented.
- M-050 bounded runtime slice implemented.
- MVP Runtime Implementation Phase 1 block completed.
- Final phase decision: `Continue bounded MVP runtime implementation`.
- Recommended next step: `prepare the next separately approved bounded runtime step without broad deferred-runtime opening`.
- Current governance truth: `M-049` and `M-050` are `BOUNDED_IMPLEMENTED` for internal metadata/control only; `M-052..M-055` remain non-broad-runtime late slots.
- Updated roadmap Phase I1 is now complete as a bounded metadata-control slice with `M-049`, `M-050`, runtime trace ledger, and integrated metadata slice linkage.
- Updated roadmap next step: `design-partner pilot stabilization before broader paid-pilot motion`.

## Current Scope

- governance reconciliation layer for canonical-vs-implemented mapping
- canonical deal records with `deal_id`
- canonical customer registry with `customer_id`
- canonical tender import runs/events/payloads
- canonical tender normalization sets/records/links
- canonical intake priority artifacts
- canonical requirement extraction artifacts
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
- persisted bid document collections, bid packages, completeness checks, bid readiness reports, and submission readiness helper gates
- canonical submission archive sets, records, and archive items
- canonical procedure monitor sets, records, events, and alerts
- canonical contract negotiation workspaces, issues, and comments
- canonical supplier contract drafts, obligations, and comments
- canonical execution plans, milestones, and planning assumptions
- canonical purchase order sets, records, items, and links
- canonical supplier progress sets, records, events, and alerts
- canonical logistics tracking sets, records, events, and links
- canonical incident register sets, records, events, and flags
- canonical acceptance control sets, records, remarks, and resolution items
- canonical closing docs sets, records, items, and flags
- canonical payment tracking sets, records, events, and alerts
- canonical claim trigger sets, records, flags, and links
- canonical deal closure report sets, records, and source links
- canonical postmortem sets, records, findings, and action items
- canonical supplier rating update sets, records, and factor breakdowns
- canonical knowledge asset sets, records, payloads, and source links
- persisted submission execution sets, attempts, receipts, post-submission trackers, and explicit outcomes
- persisted delivery launch controls, execution command centers, milestones, fulfillment, shipping/acceptance, and payment collection records
- persisted incidents, deal closure/archive snapshots, and KPI/learning outputs
- persisted dashboard snapshots, archive export manifests, and automated learning recommendations
- helper closure, KPI, archive export, and dashboard contours preserved as compatibility bridges under recovered `M-045..M-048`
- persisted workflow runs, optimization recommendations, and operator copilot feeds
- persisted connector registries, connector sync runs, workspace feeds, and controlled action queues
- persisted integration tasks, operator sessions, and gated execution ledger runs/results
- persisted vendor connector profiles, operator action console snapshots, and external execution gateway calls/results as non-canonical internal extensions
- persisted pre-L1 launch visibility sets, records, and items as an internal pilot-support helper
- FastAPI endpoints, Alembic migrations, seed data, and integration tests

## Implementation Summary

- Stack: `FastAPI + SQLAlchemy 2 + Alembic + Pydantic + pytest`
- Runtime target: PostgreSQL
- Test runtime: SQLite in-memory for fast integration coverage
- Default status on create: `NEW`
- Business IDs are generated in application code with DB uniqueness guarantees and retry-friendly formatting.
- AI/LLM, prompt, agent, and external platform execution work are intentionally deferred until after recovery review and Launch Sprint `L1`.
- Public repository state is now synchronized at `2bbd379` with `origin/main` matching local `main`. Both branches are at parity.
- The repository includes both the Dry Run 0 planning package and the filled result package: scenario, execution log, review result, blockers/non-blockers, and success criteria.
- The list below is an implementation inventory and includes both canonical-business refs and internal-extension refs currently present in code:
  - `DL-YYYY-NNNNNN`
  - `CUS-YYYY-NNNNNN`
  - `ART-YYYY-NNNNNN`
  - `EVT-YYYY-NNNNNN`
  - `DEC-YYYY-NNNNNN`
  - `INT-YYYY-NNNNNN`
  - `TIR-YYYY-NNNNNN`
  - `TIE-YYYY-NNNNNN`
  - `TNS-YYYY-NNNNNN`
  - `TN-YYYY-NNNNNN`
  - `IPS-YYYY-NNNNNN`
  - `IP-YYYY-NNNNNN`
  - `RES-YYYY-NNNNNN`
  - `REQ-YYYY-NNNNNN`
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
  - `SC-YYYY-NNNNNN`
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
  - `BRR-YYYY-NNNNNN`
  - `SRS-YYYY-NNNNNN`
  - `SR-YYYY-NNNNNN`
  - `SAR-YYYY-NNNNNN`
  - `PMS-YYYY-NNNNNN`
  - `PM-YYYY-NNNNNN`
  - `PME-YYYY-NNNNNN`
  - `CNS-YYYY-NNNNNN`
  - `CN-YYYY-NNNNNN`
  - `EPS-YYYY-NNNNNN`
  - `EP-YYYY-NNNNNN`
  - `EPM-YYYY-NNNNNN`
  - `POS-YYYY-NNNNNN`
  - `PO-YYYY-NNNNNN`
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
  - `SPS-YYYY-NNNNNN`
  - `SP-YYYY-NNNNNN`
  - `SPE-YYYY-NNNNNN`
  - `LTS-YYYY-NNNNNN`
  - `LT-YYYY-NNNNNN`
  - `LTE-YYYY-NNNNNN`
  - `IRS-YYYY-NNNNNN`
  - `IR-YYYY-NNNNNN`
  - `IRE-YYYY-NNNNNN`
  - `ACS-YYYY-NNNNNN`
  - `ACC-YYYY-NNNNNN`
  - `CDS-YYYY-NNNNNN`
  - `CD-YYYY-NNNNNN`
  - `PTS-YYYY-NNNNNN`
  - `PT-YYYY-NNNNNN`
  - `PTE-YYYY-NNNNNN`
  - `CTS-YYYY-NNNNNN`
  - `CT-YYYY-NNNNNN`
  - `DCRS-YYYY-NNNNNN`
  - `DCR-YYYY-NNNNNN`
  - `POMS-YYYY-NNNNNN`
  - `POM-YYYY-NNNNNN`
  - `SRTS-YYYY-NNNNNN`
  - `SRT-YYYY-NNNNNN`
  - `KAS-YYYY-NNNNNN`
  - `KA-YYYY-NNNNNN`
  - `LVS-YYYY-NNNNNN`
  - `LV-YYYY-NNNNNN`
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

5. Optional: enable read-only ЕИС documentation intake locally before starting the backend.

Create `.env.local` yourself and do not commit it:

```bash
cat > .env.local <<'EOF'
ZAKUPKI_GOV_RU_SOAP_ENABLED=1
ZAKUPKI_GOV_RU_SOAP_TOKEN_OWNER=individual
ZAKUPKI_GOV_RU_SOAP_TOKEN=ВСТАВИТЬ_ТОКЕН_СЮДА
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_BASE_URL=https://int.zakupki.gov.ru/eis-integration/services/getDocsIP
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_XSD_URL=https://int.zakupki.gov.ru/eis-integration/services/getDocsIP?xsd=getDocsIP-ws-api.xsd
ZAKUPKI_GOV_RU_SOAP_INDIVIDUAL_NAMESPACE=http://zakupki.gov.ru/fz44/get-docs-ip/ws
ZAKUPKI_GOV_RU_SOAP_TOKEN_HEADER_NAME=individualPerson_token
ZAKUPKI_GOV_RU_SOAP_MODE=PROD
ZAKUPKI_GOV_RU_SOAP_DISABLE_PROXY_FOR_EIS=1
ZAKUPKI_GOV_RU_SOAP_REQUIRE_DIRECT_RU_ROUTE=1
ZAKUPKI_GOV_RU_SOAP_ALLOWED_HOSTS=zakupki.gov.ru,.zakupki.gov.ru,int.zakupki.gov.ru,int44.zakupki.gov.ru,int44-ttls-cert.zakupki.gov.ru
ZAKUPKI_GOV_RU_SOAP_USER_AGENT=ArvectumTenderAgent/0.1 read-only
ZAKUPKI_GOV_RU_SOAP_CONTENT_TYPE=text/xml; charset=utf-8
ZAKUPKI_GOV_RU_SOAP_USE_SOAP_ACTION=1
ZAKUPKI_GOV_RU_SOAP_SOAP_ACTION=http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip
ZAKUPKI_GOV_RU_SOAP_TIMEOUT_SECONDS=30
ZAKUPKI_GOV_RU_SOAP_MAX_RESULTS=10
ZAKUPKI_GOV_RU_SOAP_MAX_ATTACHMENTS=20
ZAKUPKI_GOV_RU_SOAP_MAX_DOWNLOAD_MB=200
ZAKUPKI_GOV_RU_SOAP_TRUST_ENV_PROXY=0
ZAKUPKI_GOV_RU_SOAP_DEBUG=0
EOF

set -a
source .env.local
set +a
```

For an individual-person token, the default endpoint is `https://int.zakupki.gov.ru/eis-integration/services/getDocsIP`. The legacy `services-vbs` path is kept only as experimental legal-entity mode. The SOAP namespace is `http://zakupki.gov.ru/fz44/get-docs-ip/ws`, and the default SOAPAction is `http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip`. If the actual endpoint differs, change only env configuration.

MacBook proxy note: if macOS routes normal traffic through a European PAC/proxy, all `zakupki.gov.ru` and `*.zakupki.gov.ru` hosts must still go `DIRECT`. In Python, the tender demo client also bypasses env/system proxy variables for EIS requests by default, so the read-only `getDocsIP` flow can use the machine's direct Russian route. `NO_PROXY` is still recommended explicitly for `zakupki.gov.ru,.zakupki.gov.ru,int.zakupki.gov.ru,int44.zakupki.gov.ru,int44-ttls-cert.zakupki.gov.ru`.

6. Run the API:

```bash
./.venv/bin/python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

7. Open the Tender Operator Agent demo:

```text
http://127.0.0.1:8000/demo/tender-agent
```

8. Use the first tab `Найти закупку` for `demo_local` or public HTML fallback, the second tab `Получить документацию по номеру` for read-only `getDocsIP`, the third tab `Загрузка и анализ` for local document uploads, and the fourth tab for the synthetic walkthrough. Demo runs are stored locally under `company_agent_runs/tender_operator_demo/` and do not trigger external actions.

9. Live EIS archive flow:

```text
Получить документацию по номеру -> archiveUrl -> archive download -> safe extract -> local run -> analyze -> report
```

In the `Получить документацию по номеру` tab you can now:

- enter `reestr_number`;
- keep `SOAP method = getDocsByReestrNumber`;
- choose whether to download the archive;
- choose whether to start analysis immediately after download;
- open the created run and report;
- watch the agent work journal update via polling.

Safety constraints: no login, no captcha bypass, no platform submission, no EDS/digital signature, no supplier email automation, and human-in-the-loop remains mandatory.

Optional live SOAP smoke on MacBook:

```bash
set -a
source .env.local
set +a
ZAKUPKI_GOV_RU_SOAP_LIVE_TEST=1 ./.venv/bin/python -m pytest -q tests/test_tender_operator_agent_getdocs_ip_client.py -k live
```

Diagnostics for the configured `getDocsIP` source are exposed in the demo UI cards `Диагностика ЕИС` / `Диагностика getDocsIP` and written locally to `company_agent_runs/zakupki_soap_diagnostics/` without storing the real token in UI, reports, events, or git-tracked files.

Troubleshooting:

- `Connection reset by peer` before PAC fix usually means the request is still going through the European proxy path.
- If `archive_not_ready` appears, wait and retry later; EIS may still be preparing the archive asynchronously.
- If the run is created with `manual_upload_required`, continue through the same run and add documents manually.
- Keep `NO_PROXY` explicit for all `zakupki.gov.ru` hosts when validating the MacBook live path.

## Tests

```bash
./.venv/bin/python -m pytest -q
```

Default `pytest` now stays offline-first and skips optional profiles unless you
opt in explicitly:

```bash
# local integration workflow tests
./.venv/bin/python -m pytest -q --run-integration

# PostgreSQL + pgvector checks
./.venv/bin/python -m pytest -q --run-postgres

# llama.cpp-specific tests
./.venv/bin/python -m pytest -q --run-llama-cpp

# live network tests
./.venv/bin/python -m pytest -q --run-network

# live Mac mini / runtime smoke tests
./.venv/bin/python -m pytest -q --run-network --run-live-smoke
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
- `POST /logistics-tracking/build`
- `POST /logistics-tracking/events`
- `GET /logistics-tracking/{logistics_tracking_set_id}`
- `GET /logistics-tracking`
- `GET /logistics-tracking/records/{logistics_tracking_id}`
- `POST /incident-register/build`
- `POST /incident-register/events`
- `GET /incident-register/{incident_register_set_id}`
- `GET /incident-register`
- `GET /incident-register/records/{incident_register_id}`
- `POST /acceptance-control/build`
- `GET /acceptance-control/{acceptance_control_set_id}`
- `GET /acceptance-control`
- `GET /acceptance-control/records/{acceptance_control_id}`
- `POST /closing-docs/build`
- `GET /closing-docs/{closing_docs_set_id}`
- `GET /closing-docs`
- `GET /closing-docs/records/{closing_docs_id}`
- `POST /payment-tracking/build`
- `POST /payment-tracking/events`
- `GET /payment-tracking/{payment_tracking_set_id}`
- `GET /payment-tracking`
- `GET /payment-tracking/records/{payment_tracking_id}`
- `POST /claim-triggers/build`
- `GET /claim-triggers/{claim_trigger_set_id}`
- `GET /claim-triggers`
- `GET /claim-triggers/records/{claim_trigger_id}`
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

- Reconciliation governance: [docs/99_governance/canonical_module_registry_locked.md](docs/99_governance/canonical_module_registry_locked.md), [docs/99_governance/canonical_vs_implemented_mapping.md](docs/99_governance/canonical_vs_implemented_mapping.md), [docs/99_governance/non_canonical_extension_register.md](docs/99_governance/non_canonical_extension_register.md), [docs/99_governance/registry_recovery_plan.md](docs/99_governance/registry_recovery_plan.md)
Historical architecture / implementation snapshots:
- [docs/00_architecture/Unified_Module_Registry.md](docs/00_architecture/Unified_Module_Registry.md)
- [docs/00_architecture/Module_Dependency_Map_and_MVP_Core.md](docs/00_architecture/Module_Dependency_Map_and_MVP_Core.md)
- [docs/01_sprints/MVP_First_Wave_Roadmap_and_High_Level_Spec.md](docs/01_sprints/MVP_First_Wave_Roadmap_and_High_Level_Spec.md)
- [docs/01_sprints/MVP_First_Wave_Backlog.md](docs/01_sprints/MVP_First_Wave_Backlog.md)
- [docs/01_sprints/Sprint_1_Technical_Spec.md](docs/01_sprints/Sprint_1_Technical_Spec.md)
- [docs/01_sprints/Sprint_2_Technical_Spec.md](docs/01_sprints/Sprint_2_Technical_Spec.md)
- [docs/01_sprints/Sprint_3A_Technical_Spec.md](docs/01_sprints/Sprint_3A_Technical_Spec.md)
- [docs/01_sprints/Sprint_3B_Technical_Spec.md](docs/01_sprints/Sprint_3B_Technical_Spec.md)
- [docs/01_sprints/Sprint_4A_Technical_Spec.md](docs/01_sprints/Sprint_4A_Technical_Spec.md)
- [docs/01_sprints/Sprint_4B_Technical_Spec.md](docs/01_sprints/Sprint_4B_Technical_Spec.md)
- [docs/01_sprints/Sprint_5A_Technical_Spec.md](docs/01_sprints/Sprint_5A_Technical_Spec.md)
- [docs/01_sprints/Sprint_5B_Technical_Spec.md](docs/01_sprints/Sprint_5B_Technical_Spec.md)
- [docs/01_sprints/Sprint_6A_Technical_Spec.md](docs/01_sprints/Sprint_6A_Technical_Spec.md)
- [docs/01_sprints/Sprint_6B_Technical_Spec.md](docs/01_sprints/Sprint_6B_Technical_Spec.md)
- [docs/01_sprints/Sprint_7A_Technical_Spec.md](docs/01_sprints/Sprint_7A_Technical_Spec.md)
- [docs/01_sprints/Sprint_7B_Technical_Spec.md](docs/01_sprints/Sprint_7B_Technical_Spec.md)
- [docs/01_sprints/Sprint_8A_Technical_Spec.md](docs/01_sprints/Sprint_8A_Technical_Spec.md)
- [docs/01_sprints/Sprint_8B_Technical_Spec.md](docs/01_sprints/Sprint_8B_Technical_Spec.md)
- [docs/03_entities/Entity_Catalog_Sprint_1.md](docs/03_entities/Entity_Catalog_Sprint_1.md)
- [docs/03_entities/Entity_Catalog_Sprint_2.md](docs/03_entities/Entity_Catalog_Sprint_2.md)
- [docs/03_entities/Entity_Catalog_Sprint_3A.md](docs/03_entities/Entity_Catalog_Sprint_3A.md)
- [docs/03_entities/Entity_Catalog_Sprint_3B.md](docs/03_entities/Entity_Catalog_Sprint_3B.md)
- [docs/03_entities/Entity_Catalog_Sprint_4A.md](docs/03_entities/Entity_Catalog_Sprint_4A.md)
- [docs/03_entities/Entity_Catalog_Sprint_4B.md](docs/03_entities/Entity_Catalog_Sprint_4B.md)
- [docs/03_entities/Entity_Catalog_Sprint_5A.md](docs/03_entities/Entity_Catalog_Sprint_5A.md)
- [docs/03_entities/Entity_Catalog_Sprint_5B.md](docs/03_entities/Entity_Catalog_Sprint_5B.md)
- [docs/03_entities/Entity_Catalog_Sprint_6A.md](docs/03_entities/Entity_Catalog_Sprint_6A.md)
- [docs/03_entities/Entity_Catalog_Sprint_6B.md](docs/03_entities/Entity_Catalog_Sprint_6B.md)
- [docs/03_entities/Entity_Catalog_Sprint_7A.md](docs/03_entities/Entity_Catalog_Sprint_7A.md)
- [docs/03_entities/Entity_Catalog_Sprint_8A.md](docs/03_entities/Entity_Catalog_Sprint_8A.md)
- [docs/03_entities/Entity_Catalog_Sprint_7B.md](docs/03_entities/Entity_Catalog_Sprint_7B.md)
- [docs/03_entities/Entity_Catalog_Sprint_8B.md](docs/03_entities/Entity_Catalog_Sprint_8B.md)
- [docs/00_architecture/implementation_summary_sprint_2a.md](docs/00_architecture/implementation_summary_sprint_2a.md)
- [docs/00_architecture/implementation_summary_sprint_2b.md](docs/00_architecture/implementation_summary_sprint_2b.md)
- [docs/00_architecture/implementation_summary_sprint_3a.md](docs/00_architecture/implementation_summary_sprint_3a.md)
- [docs/00_architecture/implementation_summary_sprint_3b.md](docs/00_architecture/implementation_summary_sprint_3b.md)
- [docs/00_architecture/implementation_summary_sprint_4a.md](docs/00_architecture/implementation_summary_sprint_4a.md)
- [docs/00_architecture/implementation_summary_sprint_4b.md](docs/00_architecture/implementation_summary_sprint_4b.md)
- [docs/00_architecture/implementation_summary_sprint_5a.md](docs/00_architecture/implementation_summary_sprint_5a.md)
- [docs/00_architecture/implementation_summary_sprint_5b.md](docs/00_architecture/implementation_summary_sprint_5b.md)
- [docs/00_architecture/implementation_summary_sprint_6a.md](docs/00_architecture/implementation_summary_sprint_6a.md)
- [docs/00_architecture/implementation_summary_sprint_6b.md](docs/00_architecture/implementation_summary_sprint_6b.md)
- [docs/00_architecture/implementation_summary_sprint_7a.md](docs/00_architecture/implementation_summary_sprint_7a.md)
- [docs/00_architecture/implementation_summary_sprint_7b.md](docs/00_architecture/implementation_summary_sprint_7b.md)
