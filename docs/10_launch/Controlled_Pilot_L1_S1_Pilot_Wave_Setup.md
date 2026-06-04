# Controlled Pilot L1 — Sprint S1: Pilot Wave Setup

Source: locked execution package provided by the user on `2026-06-05`.

## Purpose

Prepare a controlled pilot wave for `1` to `2` pilot deals.

## Goal

Assemble the formal setup package that allows the first real pilot deal to start safely.

## Input

- Dry Run 0 package completed
- repository ready for Dry Run 0 execution -> completed
- dry-run result: `GO with minor fixes before L1`
- launch docs and governance docs synced

## Required Work

1. Fix pilot mode:
   - internal
   - operator-assisted
   - manual-control
2. Fix:
   - owner
   - operator
   - reviewer
3. Define:
   - allowed pilot deals
   - disallowed pilot deals
   - stop rules
   - review cadence
4. Assemble templates:
   - deal intake
   - decision log

## Mandatory Deliverables

- `Controlled_Pilot_L1_Wave_Charter.md`
- `Controlled_Pilot_L1_Deal_Selection_Criteria.md`
- `Controlled_Pilot_L1_Deal_Intake_Template.md`
- `Controlled_Pilot_L1_Stop_Rules.md`
- `Controlled_Pilot_L1_Review_Cadence.md`
- `Controlled_Pilot_L1_Decision_Log_Template.md`

## Constraints

- no new canonical IDs
- no AI/runtime expansion
- no autonomous claims
- no opening `M-049/M-050`
- no turning `M-052..M-055` into full runtime

## Acceptance Criteria

1. pilot charter exists
2. deal selection criteria exists
3. intake template exists
4. stop rules exist
5. review cadence exists
6. README reflects controlled pilot phase
7. governance tests pass

## Explicit Exit Wording

`repository ready for Controlled Pilot L1 Deal #1 setup`

## Plan Alignment

This sprint must match `Controlled_Pilot_L1_Master_Plan.md` section `L1-S1`.

Any drift introduced: `NO`
