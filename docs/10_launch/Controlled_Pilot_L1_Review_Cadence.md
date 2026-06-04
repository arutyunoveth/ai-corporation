# Controlled Pilot L1 Review Cadence

## Purpose

Define the minimum review rhythm for the pilot wave.

## Wave-Level Cadence

- `Wave setup review` once after S1
- `Deal review` after each pilot deal
- `Confirmation review` after Deal #2 if Deal #2 is executed
- `Final exit review` in S4

## Deal-Level Cadence

For each pilot deal, the operator and reviewer must review at least:

1. before deal start
2. after screening / qualification
3. after supplier/commercial decision
4. after finance/risk/approval checkpoint
5. after bid/procedure checkpoint
6. after payment / claim checkpoint if reached
7. at closure / postmortem

## Helper Review Cadence

At minimum:

- `/events?deal_id=...` at every critical state transition
- `/dashboards/build` when a major stage changes
- `/workspace-feed/build` before operational handoffs
- `/action-queue/build` when manual approvals matter
- `/launch-visibility/build` at least once per active deal review window

## Review Output Requirement

Every review window must result in one of:

- continue
- continue with note
- pause for fix/review
- stop

## Plan Alignment

- Master Plan matched: yes
- What changed vs plan: review cadence is made explicit at wave, deal, and helper levels
- Any drift introduced: `NO`
