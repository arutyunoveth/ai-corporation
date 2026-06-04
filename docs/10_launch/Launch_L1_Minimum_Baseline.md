# Launch L1 Minimum Baseline

## Mandatory Before L1

1. Recovery and registry reconciliation remain accepted as complete for:
   - `M-001..M-048`
   - `M-051`
2. `M-049` and `M-050` remain explicitly closed and out of launch scope.
3. `M-052..M-055` remain documented as reconciled non-runtime slots, not disguised as fully implemented runtime modules.
4. Clean migration verification succeeds on a fresh database.
5. Full pytest suite remains green.
6. The operator team accepts a manual-control pilot model.
7. The launch package documents in `docs/10_launch/` are reviewed and accepted.

## Required Runtime Baseline

The following runtime capabilities must be usable before L1:

- deal creation and status flow
- document storage and ingestion
- event logging and decision journaling
- supplier / quote / comparison flows
- finance / risk / approval flows
- bid prep / submission / procedure monitor flows
- execution entry / logistics / acceptance / payment / claims flows
- closure / postmortem / knowledge flows

## Required Compensating Controls

### Control 1. Manual Event Review

For each active launch deal:

- review `/events?deal_id=...`
- review incident, payment, and claim records
- confirm no untriaged blocking event remains

### Control 2. Snapshot Review

For each active launch deal:

- build and review dashboard snapshot
- build and review launch visibility
- build and review workspace feed
- build and review action queue where approvals are needed

### Control 3. Risk Aggregation Review

Operators must explicitly review persisted outputs from:

- screening
- initial tech risks
- contract risks
- integrated risk memo
- incident register
- payment tracking
- claim triggers

### Control 4. Human Handoff Discipline

- no silent state handoffs
- no assumed autonomous follow-up
- every critical transition must have an identified owner

## What Can Be Deferred Until After L1

- `M-049 Agent Registry`
- `M-050 Prompt / Schema Library`
- standalone runtime realization of `M-052 Notification Layer`
- standalone runtime realization of `M-053 Red Flag Registry`
- standalone runtime realization of `M-054 Master Dashboard`
- standalone runtime realization of `M-055 SaaS Productization Tracker`
- polished UI or portfolio-grade operational cockpit

## Launch Restrictions

L1 is acceptable only under the following restrictions:

- pilot mode only
- operator-assisted only
- no unattended monitoring assumptions
- no real-time notification guarantees
- no autonomous external execution
- no self-serve SaaS claims

## Minimum Acceptance Statement

If all controls above are in place, the current repository is sufficient for Launch Sprint `L1` as a controlled internal pilot.

If any of these controls are rejected, launch should pause for a mini-gap closure step.

The current mini-gap closure step adds a launch-support helper for visibility and attention aggregation without reopening deferred canonical runtime slots.
