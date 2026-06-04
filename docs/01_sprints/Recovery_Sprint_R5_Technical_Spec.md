# Recovery Sprint R5 Technical Spec

## Objective

Restore the remaining post-deal canonical modules from the original recovery catalog without introducing AI/LLM/runtime automation.

## Modules

- `M-045` Deal Closure Report
- `M-046` Postmortem Builder
- `M-047` Supplier Rating Updater
- `M-048` Knowledge Asset Builder

## Inputs

- canonical `M-035..M-044`
- helper `deal_closure`
- helper `kpi_learning`
- helper `archive_export`
- helper `dashboard_snapshots`

## Required Outputs

- persisted canonical `M-045..M-048` entities
- event-log continuity for set creation, record creation, status changes, and handoffs
- final recovery audit with explicit `M-049/M-050` status

## Non-Goals

- no AI/LLM integration
- no prompt or schema runtime
- no agent execution
- no external platform actions
- no destructive refactor
