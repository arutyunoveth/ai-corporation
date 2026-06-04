# Launch L1 Control Gates

## Purpose

This table defines mandatory human-control gates for the `L1` pilot.

No gate may be bypassed by helper contours, workflow traces, or recommendation outputs.

The same gates must be exercised during `Dry Run 0`.

## Control Gates

| Gate | When it occurs | Operator must review | Primary runtime artifacts | Stop condition |
|---|---|---|---|---|
| Screening review gate | after early qualification | screening outcome, reasons, missing prerequisites | `screening`, `intake-priority`, `requirements` | stop if `FAIL`, unclear `NEEDS_REVIEW`, or missing critical docs |
| Supplier selection review gate | before supplier choice | supplier shortlist, verification, quote comparison rationale | `supplier-search`, `supplier-verification`, `quote-comparison` | stop if preferred supplier is not human-approved |
| Finance / risk approval gate | before formal approval | cost, cash gap, financing, risk memo, contract risk | `cost-model`, `cash-gap`, `financing-strategy`, `finance-memo`, `contract-risks`, `integrated-risk-memo`, `ceo-approval` | stop if risk/finance assumptions are unresolved |
| Final bid / sign gate | before submission action | collected docs, package, completeness, readiness | `bid-documents`, `bid-packages`, `bid-completeness`, helper `submission-readiness` | stop if package is incomplete or human sign-off is absent |
| Procedure outcome review gate | after bid result or procedure update | outcome, monitor events, negotiation context | `procedure-monitor`, helper `outcome-intake`, `contract-negotiation` | stop if outcome path is unclear or contested |
| Contract negotiation review gate | before execution entry | negotiation issues, supplier contract, execution assumptions | `contract-negotiation`, `supplier-contracts`, `execution-plans`, `purchase-orders` | stop if obligations or terms are unresolved |
| Payment / claim review gate | during and after execution | payment status, overdue events, claim triggers, incidents | `payment-tracking`, `claim-triggers`, `incident-register`, `acceptance-control` | stop if overdue/claim conditions are unreviewed |

## Helper Support Allowed At Gates

Operators may also use:

- `GET /events?deal_id=...`
- `POST /dashboards/build`
- `POST /workspace-feed/build`
- `POST /action-queue/build`

These helper contours support the gate.

They do not replace the gate.

## Mandatory Escalation Rule

If a gate cannot be resolved confidently from persisted artifacts:

1. pause progression
2. append or review missing event/decision entries
3. escalate to the human owner
4. document the reason in the audit trail
