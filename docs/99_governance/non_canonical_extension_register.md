# Non-Canonical Extension Register

## Purpose

This register lists useful implemented layers that should not be treated as canonical business modules.

Two classes exist:

1. `Canonical-slot drift`
   Current code occupies a canonical `M-0xx` slot with a different concept than the locked registry expects.
2. `Extra non-canonical IDs`
   Implemented modules beyond the locked business range `M-001..M-055`.

## A. Canonical-Slot Drift

| Current implemented module | Current slot | Why it is useful | Recommended canonical destination |
|---|---|---|---|
| Tender Summary Builder | current `M-012` | Useful persisted intake artifact | Internal helper / submodule under M-008, M-011, future canonical M-012 |
| Submission Readiness Gate | current `M-032` | Useful pre-submit gating logic | Helper under M-031 / future canonical submission archive flow |
| Submission Control | current `M-033` | Useful controlled submission execution | Internal submission helper under canonical M-032/M-033 recovery |
| Submission Receipt Registry | current `M-035` | Useful persisted evidence layer | Helper under canonical M-032 Submission Archive |
| Post-Submission Tracker | current `M-036` | Useful ongoing status timeline | Helper under canonical M-033 Tender Procedure Monitor |
| Outcome Intake | current `M-037` | Useful formal outcome capture | Helper under canonical M-033 Tender Procedure Monitor |
| Delivery Launch Control | current `M-039` | Useful award-to-execution launch control | Helper around canonical M-036 Execution Plan Builder |
| Execution Command Center | current `M-040` | Useful execution cockpit | Helper around canonical M-036 and M-038 |
| Delivery Milestone Tracker | current `M-041` | Useful milestone trace | Helper around canonical M-036, M-038, M-041 |
| Supplier Fulfillment Tracker | current `M-042` | Useful vendor-side execution tracking | Helper around canonical M-037, M-038 |
| Shipping & Acceptance Tracker | current `M-043` | Useful logistics and acceptance trace | Split between canonical M-039 and M-041 |
| Payment Collection Tracker | current `M-044` | Useful receivables tracking | Helper under canonical M-043 Payment Tracker |
| Incident & Escalation Desk | current `M-045` | Useful operational incident handling | Helper under canonical M-040 Incident Register |
| Deal Closure & Archive | current `M-046` | Useful closure state and archive snapshot | Split between canonical M-045 and archive helper |
| KPI & Learning Loop | current `M-047` | Useful KPI and retrospective signals | Split between canonical M-046, M-047, M-048 |
| Operational Dashboard Backbone | current `M-048` | Useful persisted dashboard snapshot layer | Helper under canonical M-054 Master Dashboard |
| Archive Export & Handover | current `M-049` | Useful export artifact layer | Helper under canonical M-048 Knowledge Asset Builder or closure/postmortem export |
| Learning Automation Engine | current `M-050` | Useful recommendation layer | Helper under canonical M-048 / M-055 |
| Optimization Recommendation Engine | current `M-052` | Useful operational recommendation engine | Helper under canonical M-046 / M-048 / M-055 |
| Operator Copilot Feed | current `M-053` | Useful operator UX feed | Internal UI-support contour |
| Connector Registry & Sync Backbone | current `M-054` | Useful integration inventory and sync layer | Platform helper under canonical M-055 Integration Bus |
| Operator Workspace Feed API | current `M-055` | Useful operator-facing workspace projection | Internal platform/UI layer |

## B. Extra Non-Canonical IDs Outside the Lock

| Current implemented module | Current slot | Why it is useful | Recommended destination |
|---|---|---|---|
| Controlled Action Queue | `M-056` | Human approval and action gating | Internal platform/control layer under canonical M-055 |
| Integration Task Adapter Layer | `M-057` | Formalized connector-ready tasks | Internal adapter layer under canonical M-055 |
| Operator Session Workspace | `M-058` | Persisted operator work sessions | Internal operator support layer |
| Gated Action Execution Ledger | `M-059` | Controlled internal execution trace | Internal execution-control layer |
| Vendor Connector Profiles | `M-060` | Vendor-facing projection over connectors | Internal connector layer under canonical M-055 |
| Operator Action Console Backbone | `M-061` | Action-oriented operator snapshot | Internal operator UX layer |
| External Execution Gateway Ledger | `M-062` | Formal external execution bridge | Internal external-execution layer under canonical M-055 |

## Governance Rule

These modules are allowed to exist in code and remain useful.

They are not allowed to redefine canonical business identity.

Until a later refactor happens:

- keep endpoints and schema stable
- keep migrations untouched
- keep runtime working
- document them as internal/support extensions, not as new business canon
