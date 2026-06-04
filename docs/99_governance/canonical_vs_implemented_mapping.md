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
| M-005 | Counterparty / Customer Registry | No dedicated business module found | MISSING | Add as canonical module later |
| M-006 | Supplier Registry | Implemented as supplier registry | EXACT | Keep |
| M-007 | Source / Tender Import Layer | Partially covered by intake/source ingestion logic | PARTIAL | Separate canonical import responsibilities from current intake flow |
| M-008 | Tender Normalization Layer | Partially covered by tender intake pipeline and summary helpers | PARTIAL | Split intake from normalization explicitly |
| M-009 | Tender Screening Engine | Implemented | EXACT | Keep |
| M-010 | Intake Summary / Prioritization | Partially covered by priority scoring and intake summary logic | PARTIAL | Reconcile into one canonical prioritization artifact |
| M-011 | Document Ingestion Layer | Implemented | EXACT | Keep |
| M-012 | Requirement Extraction from Tender Docs | Canonical intent not implemented as top-level module; current `M-012` is tender summary builder | MISMATCH | Restore canonical M-012; move current tender summary under internal/helper contour |
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
| M-031 | Bid Completeness Checker | Implemented, but part of readiness logic drifted outward | PARTIAL | Pull readiness logic closer to canonical completeness contour |
| M-032 | Submission Archive | Current `M-032` is submission readiness gate, not archive | MISMATCH | Recover M-032 as archive module; keep current readiness as helper/submodule |
| M-033 | Tender Procedure Monitor | Current `M-033` is submission control | MISMATCH | Recover M-033 monitor; reclass current submission control as helper contour |
| M-034 | Contract Negotiation Workspace | Not found | MISSING | Add later as canonical business module |
| M-035 | Supplier Back-to-Back Contract Draft | Current `M-035` is submission receipt registry | MISMATCH | Recover canonical supplier contract draft |
| M-036 | Execution Plan Builder | Current `M-036` is post-submission tracker | MISMATCH | Recover canonical execution plan builder |
| M-037 | Purchase Order Manager | Current `M-037` is outcome intake | MISMATCH | Recover canonical PO manager |
| M-038 | Supplier Progress Monitor | Not found as canonical top-level | MISSING | Add later |
| M-039 | Logistics Tracker | Current `M-039` is delivery launch control | MISMATCH | Recover logistics tracker; keep launch control as helper contour |
| M-040 | Incident Register | Current `M-040` is execution command center | MISMATCH | Recover incident register |
| M-041 | Acceptance Control | Current `M-041` is delivery milestone tracker | MISMATCH | Recover acceptance control |
| M-042 | Closing Docs Pack Builder | Current `M-042` is supplier fulfillment tracker | MISMATCH | Recover canonical closing docs module |
| M-043 | Payment Tracker | Current `M-043` is shipping and acceptance tracker | MISMATCH | Recover canonical payment tracker |
| M-044 | Claims Trigger Engine | Current `M-044` is payment collection tracker | MISMATCH | Recover canonical claims trigger |
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
| EXACT | 26 | M-001, M-002, M-003, M-004, M-006, M-009, M-011, M-013..M-030, M-051 |
| PARTIAL | 4 | M-007, M-008, M-010, M-031 |
| MISMATCH | 22 | M-012, M-032, M-033, M-035..M-037, M-039..M-050, M-052..M-055 |
| MISSING | 3 | M-005, M-034, M-038 |

## Key Findings

1. Early and middle business flow coverage is strong through supplier, finance, and most bid-prep contours.
2. Registry drift becomes material from the later submission / execution / governance / platform area.
3. The main governance problem is not lack of useful implementation, but reuse of canonical IDs for non-canonical concepts.
