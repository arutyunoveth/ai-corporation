# Launch L1 Pilot Playbook

## Pilot Scope

This playbook becomes operational only after `Dry Run 0` is completed, reviewed, and the agreed minor pre-`L1` follow-ups are closed or explicitly accepted.

Launch Sprint `L1` is limited to:

- `1` to `2` pilot deals
- internal usage only
- operator-assisted mode only
- explicit manual supervision

## Pilot Objectives

The pilot is meant to validate:

1. that the recovered canonical runtime is usable end-to-end
2. that operators can control the lifecycle without hidden blockers
3. that helper visibility layers are sufficient for pilot supervision
4. that the main pain points before a broader launch are visible

The pilot is not meant to prove:

- autonomous operation
- AI-native orchestration
- self-serve product readiness
- real-time notification quality
- portfolio-scale management

## How To Run Pilot Deals

For each pilot deal:

1. create and normalize the opportunity inside the canonical intake flow
2. progress it through screening, supplier, finance, bid, and execution stages only with manual control gates
3. force explicit human review at the checkpoints listed in [Launch_L1_Control_Gates.md](/Users/master/Documents/AI-Corporation/docs/10_launch/Launch_L1_Control_Gates.md)
4. use event log, dashboard snapshots, workspace feed, and action queue as control aids
5. capture every material failure, ambiguity, or delay

## What Must Be Logged Manually

- operator owner for each phase
- any ambiguity not resolved by canonical artifacts
- any reason to stop, delay, or escalate a deal
- pain points where operators had to search across too many artifacts
- missing visibility signals
- any step that felt unsafe without notification or dashboard support

## What Must Be Reviewed Manually

- screening outcomes
- supplier selection recommendation
- finance and integrated risk outputs
- approval decision
- bid completeness result
- procedure outcome
- contract negotiation issues
- payment delays and claim triggers
- closure and postmortem findings

## Pilot Success Criteria

A pilot deal is considered operationally successful when:

- the canonical runtime chain completes without structural blocker
- event log continuity remains intact
- human reviewers can identify and control major risk points
- final closure and learning artifacts are persisted

## Pilot Failure Signals

Escalate to a mini-gap closure sprint if:

- operators repeatedly miss critical events
- required decisions are too hard to surface manually
- dashboard/workspace helper contours are insufficient
- payment / claim / incident issues cannot be supervised safely
- the team is pressured to describe the system as more autonomous than it is

## Exit Decision After Pilot

After `1` to `2` pilot deals, choose one path:

1. continue controlled pilot mode
2. run a mini-gap closure sprint for ops visibility
3. begin later post-launch planning for reserved AI/runtime slots
