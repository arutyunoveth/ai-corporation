# Steady-State Usage Cadence Rules

## Cycle Cadence

Each steady-state cycle must follow:

1. entry check
2. execution by runbook and control gates
3. helper rebuild/review pass
4. review result and explicit continue/pause/stop decision

## Rebuild / Review Cadence

Required helper sequence remains explicit:

1. `/events?deal_id=...`
2. `/dashboards/build`
3. `/workspace-feed/build`
4. `/action-queue/build`
5. `/launch-visibility/build`

## Cadence Discipline

- no cycle may close without filled execution and review artifacts
- no next cycle may start before prior review is completed
- manual cadence is a feature of the phase, not a bug to hide
