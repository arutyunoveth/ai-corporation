# Pre-L1 Owner Overview

## Purpose

Give the pilot owner a compact persisted view of:

- active pilot deals
- blocked deals
- manual-review pressure
- overdue/payment pressure
- current operator hotspots

## How To Build

Deal view:

```text
POST /launch-visibility/build
{
  "scope_type": "DEAL",
  "scope_ref": "DL-2026-000001"
}
```

Pilot view:

```text
POST /launch-visibility/build
{
  "scope_type": "PILOT",
  "scope_ref": "L1-PILOT"
}
```

## Metrics Produced

Each persisted launch visibility record currently stores:

- `active_deal_count`
- `blocked_deal_count`
- `attention_count`
- `red_flag_count`
- `manual_review_count`
- `overdue_count`

## Recommended L1 Review Flow

1. Build pilot overview at the beginning of the operating window.
2. Review blocked deals first.
3. Review all overdue and claim-related items.
4. Review all incident and acceptance items.
5. Review action hotspots for unresolved follow-up.

## What This Is Not

This is not:

- canonical `M-054 Master Dashboard`
- a real-time owner cockpit
- a self-serve SaaS dashboard
- an AI operator panel

It is a small pre-launch support layer for a controlled pilot.
