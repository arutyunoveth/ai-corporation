# Pre-L1 Ops Visibility Package

## Purpose

Before Launch Sprint `L1`, the repository adds a minimal launch-support helper for operator visibility and manual control comfort.

This package exists to reduce the launch-audit pain points around:

- important event visibility
- cross-module red-flag aggregation
- owner/operator launch overview
- manual-control ergonomics

It does **not** open:

- `M-049 Agent Registry`
- `M-050 Prompt / Schema Library`
- standalone runtime `M-052 Notification Layer`
- standalone runtime `M-053 Red Flag Registry`
- standalone runtime `M-054 Master Dashboard`
- standalone runtime `M-055 SaaS Productization Tracker`

## Runtime Support Added

Internal helper contour:

- `launch_visibility_sets`
- `launch_visibility_records`
- `launch_visibility_items`

Business refs:

- `launch_visibility_set_id` -> `LVS-YYYY-NNNNNN`
- `launch_visibility_id` -> `LV-YYYY-NNNNNN`

Endpoints:

- `POST /launch-visibility/build`
- `GET /launch-visibility/{launch_visibility_set_id}`
- `GET /launch-visibility`
- `GET /launch-visibility/records/{launch_visibility_id}`

Event codes:

- `launch_visibility_built`
- `launch_visibility_item_recorded`
- `launch_visibility_failed`

Source module id for event trace:

- `L1-SUPPORT`

This is intentional. The helper is tracked as a pilot-support contour and not as a canonical business module.

## Scope Types

- `DEAL`
- `PILOT`

`DEAL` scope aggregates attention and red flags for one deal.

`PILOT` scope aggregates attention and red flags across all currently persisted deals to give the owner/operator a compact pilot overview.

## Aggregation Sources

The helper reads persisted outputs only. It does not inspect raw files or transient UI state.

Current aggregation sources:

- `M-009` screening
- `M-015` initial tech risks
- `M-026` contract risks
- `M-033` procedure monitor
- `M-038` supplier progress
- `M-040` incident register
- `M-041` acceptance control
- `M-043` payment tracking
- `M-044` claim triggers
- helper `workspace_feed`
- helper `action_queue`

## Why This Does Not Violate Locked Registry

1. No new canonical `M-*` slot is introduced.
2. No deferred slot is reclassified as “fully implemented runtime”.
3. No AI/LLM/prompt/agent runtime is introduced.
4. No autonomous notifications or external actions are promised.
5. The helper is explicitly documented as pre-launch support only.

## Known Limits

- no real-time delivery guarantees
- no push notification transport
- no autonomous escalation
- no portfolio-grade dashboard claims
- no replacement for canonical governance status of `M-052..M-055`

## Launch Decision Effect

This package upgrades the repository from:

- `GO with restrictions`

to:

- `GO with restrictions and improved operator visibility`

The pilot remains:

- controlled
- internal
- human-operated
- manually reviewed
