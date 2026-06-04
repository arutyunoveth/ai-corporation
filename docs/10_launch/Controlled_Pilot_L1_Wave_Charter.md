# Controlled Pilot L1 Wave Charter

## Purpose

This charter authorizes the first controlled pilot wave after Dry Run 0.

## Pilot Mode

The pilot wave is restricted to:

- internal
- pilot-scale
- operator-assisted
- manual-control

The wave must not be described as:

- autonomous
- AI-native runtime
- self-serve
- broad launch

## Wave Scope

- target volume: `1` to `2` pilot deals
- execution order:
  1. pilot deal #1
  2. pilot deal #2 only after explicit review of deal #1
- allowed repository state: current locked-registry, post-dry-run state

## Required Roles

The following roles are mandatory for every pilot deal:

- `Pilot Owner`
  - accepts scope, follow-ups, and final deal outcome
- `Pilot Operator`
  - executes the runbook and keeps logs current
- `Pilot Reviewer`
  - verifies gate decisions, blockers, and go/no-go wording

No pilot deal may start without all three roles assigned explicitly in the intake template.

## Required Controls

- manual gate review at screening, supplier selection, finance/risk, bid/procedure, contract/execution entry, payment/claim, and closure
- explicit review of `/events?deal_id=...`
- explicit review of visibility helpers when needed:
  - `/dashboards/build`
  - `/workspace-feed/build`
  - `/action-queue/build`
  - `/launch-visibility/build`

## Deliverable Discipline

Each pilot deal must produce:

- intake record
- execution log
- review result
- blockers/non-blockers summary
- explicit next-step decision

## Status

Wave status after S1:

`repository ready for Controlled Pilot L1 Deal #1 setup`

## Plan Alignment

- Master Plan matched: yes
- What changed vs plan: repo-local pilot-wave deliverables were materialized from the locked package
- Any drift introduced: `NO`
