# Canonical Vs Implemented Mapping

## Legend

- `EXACT` — implemented close to canonical meaning and slot.
- `PARTIAL` — partially implemented or spread across adjacent modules/helpers.
- `MISMATCH` — the canonical ID is currently occupied by a different implemented concept.
- `MISSING` — the canonical module is not implemented as a distinct business module.
- `DRIFT` — used only for non-canonical extensions, not for the canonical table below.

## Canonical Coverage Table

| Canonical ID | Canonical module | Current repo coverage | Status | Recommended action |
|---|---|---|---|---|
| M-001 | Deal Card Core | Implemented as central deal registry and core deal records | EXACT | Keep; only align wording in docs over time |
| M-002 | Deal Status Model | Implemented as formal status engine | EXACT | Keep |
| M-003 | Document Store | Implemented | EXACT | Keep |
| M-004 | Event Log & Decision Journal | Implemented | EXACT | Keep |
| M-005 | Counterparty / Customer Registry | Implemented as customer registry with profiles, refs, and contours | EXACT | Keep |
| M-006 | Supplier Registry | Implemented as supplier registry | EXACT | Keep |
| M-007 | Source / Tender Import Layer | Implemented as raw tender import run/event/payload layer | EXACT | Keep |
| M-008 | Tender Normalization Layer | Implemented as explicit normalization set/record/link contour | EXACT | Keep |
| M-009 | Tender Screening Engine | Implemented | EXACT | Keep |
| M-010 | Intake Summary / Prioritization | Implemented as canonical intake priority artifact with factors | EXACT | Keep |
| M-011 | Document Ingestion Layer | Implemented | EXACT | Keep |
| M-012 | Requirement Extraction from Tender Docs | Implemented as explicit requirement extraction module; legacy tender summary remains helper contour | EXACT | Keep |
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
| M-031 | Bid Completeness Checker | Implemented as canonical completeness set/record/flag layer with explicit `bid_readiness_reports`; legacy submission readiness remains helper contour | EXACT | Keep |
| M-032 | Submission Archive | Implemented as canonical archive set/record/item layer over submitted execution and receipt evidence | EXACT | Keep |
| M-033 | Tender Procedure Monitor | Implemented as canonical procedure monitor over helper post-submission and outcome contours | EXACT | Keep |
| M-034 | Contract Negotiation Workspace | Implemented as canonical negotiation workspace over won outcome and contract risk helpers | EXACT | Keep |
| M-035 | Supplier Back-to-Back Contract Draft | Implemented as canonical supplier contract set/record/obligation/comment layer over negotiation and quote helpers | EXACT | Keep |
| M-036 | Execution Plan Builder | Implemented as canonical execution plan set/record/milestone/assumption layer over helper milestone context | EXACT | Keep |
| M-037 | Purchase Order Manager | Implemented as canonical purchase order set/record/item/link layer over contract and execution plan context | EXACT | Keep |
| M-038 | Supplier Progress Monitor | Implemented as canonical supplier progress set/record/event/alert layer over purchase order and fulfillment helpers | EXACT | Keep |
| M-039 | Logistics Tracker | Implemented as canonical logistics tracking set/record/event/link layer over purchase order, supplier progress, and shipping helpers | EXACT | Keep |
| M-040 | Incident Register | Implemented as canonical incident register set/record/event/flag layer over logistics and helper incident/payment context | EXACT | Keep |
| M-041 | Acceptance Control | Implemented as canonical acceptance set/record/remark/resolution layer over logistics and shipping helpers | EXACT | Keep |
| M-042 | Closing Docs Pack Builder | Implemented as canonical closing docs set/record/item/flag layer over acceptance and delivery context | EXACT | Keep |
| M-043 | Payment Tracker | Implemented as canonical payment tracking set/record/event/alert layer over closing docs and collection helpers | EXACT | Keep |
| M-044 | Claims Trigger Engine | Implemented as canonical claim trigger set/record/flag/link layer over payment and incident context | EXACT | Keep |
| M-045 | Deal Closure Report | Current `M-045` is incident and escalation desk | MISMATCH | Recover canonical closure report |
| M-046 | Postmortem Builder | Current `M-046` is deal closure and archive | MISMATCH | Recover canonical postmortem builder |
| M-047 | Supplier Rating Updater | Current `M-047` is KPI and learning loop | MISMATCH | Recover canonical supplier rating updater |
| M-048 | Knowledge Asset Builder | Current `M-048` is operational dashboard backbone | MISMATCH | Recover canonical knowledge asset builder |
| M-049 | Agent Registry | Current `M-049` is archive export and handover | MISMATCH | Recover canonical agent registry |
| M-050 | Prompt / Schema Library | Current `M-050` is learning automation engine | MISMATCH | Recover canonical prompt/schema library |
| M-051 | Workflow Orchestrator | Implemented as workflow orchestration backbone | EXACT | Keep; align naming only |
| M-052 | Notification Layer | Current `M-052` is optimization recommendation engine | MISMATCH | Recover canonical notification layer |
| M-053 | Red Flag Registry | Current `M-053` is operator copilot feed | MISMATCH | Recover canonical red flag registry |
| M-054 | Master Dashboard | Current `M-054` is connector registry and sync backbone | MISMATCH | Recover canonical master dashboard |
| M-055 | SaaS Productization Tracker | Current `M-055` is operator workspace feed API | MISMATCH | Recover canonical SaaS productization tracker |

## Coverage Summary

| Status | Count | Canonical IDs |
|---|---:|---|
| EXACT | 45 | M-001..M-044, M-051 |
| PARTIAL | 0 | None |
| MISMATCH | 10 | M-045..M-050, M-052..M-055 |
| MISSING | 0 | None |

## Key Findings

1. Early intake and analysis recovery is canonical through `M-012`, and late delivery/payment recovery is now canonical through `M-044`.
2. Registry drift is now concentrated in `M-045..M-055`.
3. The main remaining governance problem is reuse of later canonical IDs for helper/platform concepts, not lack of useful implementation.
