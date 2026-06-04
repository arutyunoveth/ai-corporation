# Non-Canonical Extension Register

## Purpose

This register lists useful implemented layers that should not be treated as canonical business modules.

Two classes exist:

1. `Historical helper drift`
   The codebase contains helper contours that historically used canonical slot numbers in earlier sprints.
2. `Extra non-canonical IDs`
   Implemented modules beyond the locked business range `M-001..M-055`.

## A. Historical Helper Drift

| Helper contour | Historical slot | Why it remains useful | Canonical destination |
|---|---|---|---|
| Legacy Tender Summary Builder package | legacy `tender_summary` contour | Backward-compatible persisted intake artifact | Internal helper under canonical `M-008`, `M-011`, `M-012` |
| Submission Readiness Gate | legacy `submission_readiness` contour | Useful pre-submit gating logic | Helper under canonical `M-031` |
| Submission Control | historical `M-033` runtime contour | Useful controlled submission execution | Helper under canonical `M-032` / `M-033` |
| Submission Receipt Registry | historical `M-035` runtime contour | Useful receipt/evidence persistence | Helper under canonical `M-032` |
| Post-Submission Tracker | historical `M-036` runtime contour | Useful ongoing timeline | Helper under canonical `M-033` |
| Outcome Intake | historical `M-037` runtime contour | Useful formal outcome capture | Helper under canonical `M-033` and `M-034` |
| Delivery Launch Control | historical `M-039` runtime contour | Useful award-to-execution launch control | Helper around canonical `M-036` |
| Execution Command Center | historical `M-040` runtime contour | Useful execution cockpit | Helper around canonical `M-036` and `M-038` |
| Delivery Milestone Tracker | historical `M-041` runtime contour | Useful milestone trace | Helper around canonical `M-036` and `M-039` |
| Supplier Fulfillment Tracker | historical `M-042` runtime contour | Useful supplier-side execution trace | Helper around canonical `M-038` and `M-039` |
| Shipping & Acceptance Tracker | historical `M-043` runtime contour | Useful logistics and acceptance trace | Split between canonical `M-039` and `M-041` |
| Payment Collection Tracker | historical `M-044` runtime contour | Useful receivables state context | Helper under canonical `M-043` and `M-044` |
| Incident & Escalation Desk | historical `M-045` runtime contour | Useful operational incident handling | Helper under canonical `M-040` |
| Deal Closure & Archive | historical `M-046` runtime contour | Useful closure state and archive snapshot | Helper under canonical `M-045` and closure/archive support |
| KPI & Learning Loop | historical `M-047` runtime contour | Useful KPI and retrospective signals | Helper under canonical `M-046`, `M-047`, `M-048` |
| Operational Dashboard Backbone | historical `M-048` runtime contour | Useful persisted dashboard snapshot layer | Helper under canonical `M-048`; supporting contour for platform-only `M-054` |
| Archive Export & Handover | historical `M-049` runtime contour | Useful export artifact layer | Helper under canonical `M-048`; does not satisfy canonical `M-049` |
| Learning Automation Engine | historical `M-050` runtime contour | Useful recommendation layer | Helper under canonical `M-048` / later platform work; does not satisfy canonical `M-050` |
| Optimization Recommendation Engine | historical `M-052` runtime contour | Useful operational recommendation engine | Internal helper; does not satisfy platform-only canonical `M-052` |
| Operator Copilot Feed | historical `M-053` runtime contour | Useful operator UX feed | Internal UI-support contour; does not satisfy governance-only canonical `M-053` |
| Connector Registry & Sync Backbone | historical `M-054` runtime contour | Useful integration inventory and sync layer | Internal platform helper; does not satisfy canonical `M-054` or governance-only `M-055` |
| Operator Workspace Feed API | historical `M-055` runtime contour | Useful operator-facing workspace projection | Internal platform/UI layer; does not satisfy governance-only canonical `M-055` |

## B. Extra Non-Canonical IDs Outside the Lock

| Current implemented module | Current slot | Why it remains useful | Recommended destination |
|---|---|---|---|
| Controlled Action Queue | `M-056` | Human approval and action gating | Internal platform/control layer |
| Integration Task Adapter Layer | `M-057` | Formalized connector-ready tasks | Internal adapter layer |
| Operator Session Workspace | `M-058` | Persisted operator work sessions | Internal operator support layer |
| Gated Action Execution Ledger | `M-059` | Controlled internal execution trace | Internal execution-control layer |
| Vendor Connector Profiles | `M-060` | Vendor-facing projection over connectors | Internal connector layer |
| Operator Action Console Backbone | `M-061` | Action-oriented operator snapshot | Internal operator UX layer |
| External Execution Gateway Ledger | `M-062` | Formal external execution bridge | Internal external-execution layer |
| Pre-L1 Launch Visibility Support Layer | no canonical slot | Minimal pilot-support aggregation for visibility, attention, and owner overview | Internal launch-support helper; does not satisfy canonical `M-052..M-055` |

## Governance Rule

These modules are allowed to exist in code and remain useful.

They are not allowed to redefine canonical business identity.

Until a later refactor happens:

- keep endpoints and schema stable
- keep migrations untouched
- keep runtime working
- document them as helper/platform/compatibility contours, not as canonical business modules
