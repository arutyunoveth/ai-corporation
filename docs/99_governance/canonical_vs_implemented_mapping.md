# Canonical Vs Implemented Mapping

## Legend

- `EXACT` — implemented close to canonical meaning and slot.
- `RESERVED` — canonical slot exists in the locked plan, but implementation is intentionally deferred.
- `PLATFORM_ONLY` — canonical slot is real, but its pre-launch role is platform/support and does not require a standalone runtime module now.
- `GOVERNANCE_ONLY` — canonical slot is real, but its pre-launch role is governance/program control and does not require a standalone runtime module now.

## Canonical Coverage Table

| Canonical ID | Canonical module | Current repo coverage | Status | Recommended action |
|---|---|---|---|---|
| M-001 | Deal Card Core | Implemented as central deal registry and core deal records | EXACT | Keep |
| M-002 | Deal Status Model | Implemented as formal status engine | EXACT | Keep |
| M-003 | Document Store | Implemented | EXACT | Keep |
| M-004 | Event Log & Decision Journal | Implemented | EXACT | Keep |
| M-005 | Counterparty / Customer Registry | Implemented as customer registry with profiles and refs | EXACT | Keep |
| M-006 | Supplier Registry | Implemented as supplier registry | EXACT | Keep |
| M-007 | Source / Tender Import Layer | Implemented as raw tender import run/event/payload layer | EXACT | Keep |
| M-008 | Tender Normalization Layer | Implemented as normalization set/record/link contour | EXACT | Keep |
| M-009 | Tender Screening Engine | Implemented | EXACT | Keep |
| M-010 | Intake Summary / Prioritization | Implemented as canonical intake priority artifact with factors | EXACT | Keep |
| M-011 | Document Ingestion Layer | Implemented | EXACT | Keep |
| M-012 | Requirement Extraction from Tender Docs | Implemented; legacy tender summary remains helper | EXACT | Keep |
| M-013 | Compliance Matrix Builder | Implemented | EXACT | Keep |
| M-014 | Document Requirement Extractor | Implemented | EXACT | Keep |
| M-015 | Initial Tech Risk Flags | Implemented | EXACT | Keep |
| M-016 | Supplier Search | Implemented | EXACT | Keep |
| M-017 | RFQ Generator | Implemented | EXACT | Keep |
| M-018 | Supplier Communication Tracker | Implemented | EXACT | Keep |
| M-019 | TKP Repository | Implemented | EXACT | Keep |
| M-020 | Supplier Verification | Implemented | EXACT | Keep |
| M-021 | Quote Comparison Engine | Implemented | EXACT | Keep |
| M-022 | Cost Model Engine | Implemented | EXACT | Keep |
| M-023 | Cash Gap Calculator | Implemented | EXACT | Keep |
| M-024 | Financing Strategy Engine | Implemented | EXACT | Keep |
| M-025 | Finance Memo Builder | Implemented | EXACT | Keep |
| M-026 | Contract Risk Parser | Implemented | EXACT | Keep |
| M-027 | Integrated Risk Memo Builder | Implemented | EXACT | Keep |
| M-028 | CEO Approval Cockpit | Implemented | EXACT | Keep |
| M-029 | Bid Document Collector | Implemented | EXACT | Keep |
| M-030 | Bid Package Builder | Implemented | EXACT | Keep |
| M-031 | Bid Completeness Checker | Implemented with explicit completeness records and readiness reports | EXACT | Keep |
| M-032 | Submission Archive | Implemented as canonical archive set/record/item layer | EXACT | Keep |
| M-033 | Tender Procedure Monitor | Implemented as canonical procedure monitor | EXACT | Keep |
| M-034 | Contract Negotiation Workspace | Implemented as canonical negotiation workspace | EXACT | Keep |
| M-035 | Supplier Back-to-Back Contract Draft | Implemented as canonical supplier contract draft layer | EXACT | Keep |
| M-036 | Execution Plan Builder | Implemented as canonical execution plan layer | EXACT | Keep |
| M-037 | Purchase Order Manager | Implemented as canonical purchase order layer | EXACT | Keep |
| M-038 | Supplier Progress Monitor | Implemented as canonical supplier progress layer | EXACT | Keep |
| M-039 | Logistics Tracker | Implemented as canonical logistics tracking layer | EXACT | Keep |
| M-040 | Incident Register | Implemented as canonical incident register layer | EXACT | Keep |
| M-041 | Acceptance Control | Implemented as canonical acceptance layer | EXACT | Keep |
| M-042 | Closing Docs Pack Builder | Implemented as canonical closing docs layer | EXACT | Keep |
| M-043 | Payment Tracker | Implemented as canonical payment tracking layer | EXACT | Keep |
| M-044 | Claims Trigger Engine | Implemented as canonical claim trigger layer | EXACT | Keep |
| M-045 | Deal Closure Report | Implemented as canonical closure report set/record/link contour over helper closure and canonical payment/claims context | EXACT | Keep |
| M-046 | Postmortem Builder | Implemented as canonical postmortem set/record/finding/action contour | EXACT | Keep |
| M-047 | Supplier Rating Updater | Implemented as canonical supplier rating update set/record/factor contour | EXACT | Keep |
| M-048 | Knowledge Asset Builder | Implemented as canonical knowledge asset set/record/link contour over closure/postmortem and helper export/dashboard context | EXACT | Keep |
| M-049 | Agent Registry | Canonical slot exists, but current repo only has helper `archive_export` historically occupying the slot | RESERVED | Keep reserved until post-recovery AI/runtime phase |
| M-050 | Prompt / Schema Library | Canonical slot exists, but current repo only has helper `learning_automation` historically occupying the slot | RESERVED | Keep reserved until post-recovery AI/runtime phase |
| M-051 | Workflow Orchestrator | Implemented as workflow orchestration backbone | EXACT | Keep |
| M-052 | Notification Layer | No standalone canonical runtime module; historical `optimization` remains helper drift and signal delivery stays under event/workflow/operator support contours | PLATFORM_ONLY | Keep as explicit post-launch platform slot; do not add fake pre-launch runtime module |
| M-053 | Red Flag Registry | No standalone canonical runtime module; red-flag semantics already persist across screening/risk/incident/payment/claim artifacts and historical `copilot_feed` remains helper drift | GOVERNANCE_ONLY | Keep as governance layer over existing canonical flags; avoid duplicate registry tables |
| M-054 | Master Dashboard | No standalone canonical runtime module; helper `dashboard_snapshots` and workspace projections remain support contours and historical `connector_registry` does not own this slot | PLATFORM_ONLY | Keep as owner/platform surface; revisit only as a later platform view layer |
| M-055 | SaaS Productization Tracker | No standalone canonical runtime module; productization/connectors/operator-support helpers remain non-canonical and historical `workspace_feed` does not own this slot | GOVERNANCE_ONLY | Keep as launch/program governance slot; revisit only after Launch `L1` |

## Coverage Summary

| Status | Count | Canonical IDs |
|---|---:|---|
| EXACT | 49 | M-001..M-048, M-051 |
| RESERVED | 2 | M-049, M-050 |
| PLATFORM_ONLY | 2 | M-052, M-054 |
| GOVERNANCE_ONLY | 2 | M-053, M-055 |

## Key Findings

1. The canonical business-company skeleton is recovered exactly through `M-048`, plus canonical `M-051`.
2. `M-049` and `M-050` do exist in the original locked registry. Numbering does not skip; these slots remain explicitly reserved for post-recovery AI/runtime work.
3. `M-052..M-055` are no longer unresolved mismatches; they are now explicitly classified as non-runtime platform/governance slots.
4. Recovery Sprint `R6` intentionally does not introduce AI, LLM, prompt, agent, autonomous-decision, or external-platform execution logic.
