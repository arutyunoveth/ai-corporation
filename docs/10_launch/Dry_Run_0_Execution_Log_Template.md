# Dry Run 0 Execution Log Template

Use this template during the actual dry run.

## Header

- dry-run id:
- date/time (UTC):
- operator:
- reviewer:
- scenario reference:
- source branch / commit:

## Step Log

| Step | Control gate | Expected result | Actual result | Issue observed | Severity | Operator note |
|---|---|---|---|---|---|---|
| Repo / governance gate | N/A | Repo/docs state confirmed |  |  |  |  |
| Early procurement gate | Screening review | Screening and requirement artifacts readable |  |  |  |  |
| Supplier / commercial gate | Supplier selection review | Supplier path understandable and manually controllable |  |  |  |  |
| Finance / risk gate | Finance / risk approval | Risks and assumptions surfaced clearly |  |  |  |  |
| Bid / procedure gate | Final bid / sign, procedure outcome | Pre-submit and post-result states understandable |  |  |  |  |
| Contract / execution entry gate | Contract negotiation review | Contract/execution assumptions reviewable |  |  |  |  |
| Delivery / payment / claims gate | Payment / claim review | Blocking and overdue signals visible |  |  |  |  |
| Closure / learning gate | Final review | Closure and postmortem artifacts complete |  |  |  |  |

## Helper Visibility Checks

| Helper artifact | Built / reviewed | Expected value | Actual value | Gap observed | Note |
|---|---|---|---|---|---|
| `/events?deal_id=...` |  | Continuous audit trail |  |  |  |
| `/launch-visibility/build` |  | Aggregated attention/red flags visible |  |  |  |
| `/dashboards/build` |  | Compact status overview visible |  |  |  |
| `/workspace-feed/build` |  | Operator hotspot feed readable |  |  |  |
| `/action-queue/build` |  | Pending actions surfaced clearly |  |  |  |

## Severity Guide

- `BLOCKER` — Dry Run 0 cannot be trusted without a fix
- `HIGH` — Controlled Pilot L1 should not start before review/fix
- `MEDIUM` — Acceptable only with explicit compensating control
- `LOW` — Friction, but not launch-critical

## Summary

- structural blockers found:
- high-severity issues found:
- medium-severity friction points:
- low-severity observations:
- operator recommendation:
