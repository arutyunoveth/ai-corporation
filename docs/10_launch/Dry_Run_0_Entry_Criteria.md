# Dry Run 0 Entry Criteria

## Goal

Define the exact gate for entering `Dry Run 0`.

`Dry Run 0` is the next step after repository sync and launch-integrity validation.

It is not yet the real pilot.

## Mandatory Criteria

### Governance / Registry

- locked registry docs are accepted as current source of truth
- `M-049` and `M-050` remain closed
- `M-052..M-055` remain documented as reconciled non-runtime slots
- non-canonical extensions remain explicitly labeled as non-canonical

### Repo / Public State

- `main` is the current source-of-truth branch
- `origin/main` contains the latest recovery, reconciliation, launch, and pre-L1 visibility work
- README matches actual runtime/governance truth
- launch docs and governance docs do not contradict each other

### Runtime / Verification

- clean `alembic upgrade head` succeeds
- full `pytest` suite succeeds
- required launch docs exist
- required pre-L1 visibility docs exist

### Operational Controls

- operators know how to review:
  - `/events?deal_id=...`
  - `/launch-visibility/build`
  - `/dashboards/build`
  - `/workspace-feed/build`
  - `/action-queue/build`
- deal owners are assigned for the dry-run scope
- manual review cadence is agreed for risk / incident / payment / claim flows

## Restrictions Still In Force

- no AI/LLM runtime
- no prompt execution runtime
- no autonomous tender submission
- no real-time notification guarantee
- no self-serve SaaS claim
- no unattended operator model

## Exit Condition For Dry Run 0

`Dry Run 0` may lead to real pilot approval only if:

1. operators can execute the runbook without confusion
2. visibility helpers are sufficient for manual control
3. no public-state or governance contradiction is discovered
4. no hidden dependency on reserved/deferred runtime is discovered
