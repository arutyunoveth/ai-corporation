# Pre-L1 Attention And Red Flags

## Goal

Provide one persisted place where operators can review launch-critical items without pretending that canonical `M-053 Red Flag Registry` is fully opened as a standalone runtime module.

## Item Classes

- `OVERVIEW`
  - baseline scope summary
- `ATTENTION`
  - needs operator review soon
- `RED_FLAG`
  - blocking or near-blocking issue
- `HOTSPOT`
  - currently important operator focus item

## Current Red-Flag Inputs

- screening fail / needs-review outcomes
- high or critical technical risks
- high contract-risk flags
- procedure alerts
- open/escalated incident-register states
- overdue/disputed payment signals
- triggered/escalated claim signals
- delayed or blocked supplier progress
- unresolved acceptance issues

## Current Hotspot Inputs

- latest persisted workspace-feed items
- latest persisted action-queue items

These hotspot sources are optional enrichments. The visibility layer must still work even if those helper contours were not built for a given deal.

## Operator Review Cadence

For each active pilot deal:

1. build `DEAL` launch visibility
2. inspect `RED_FLAG` items first
3. inspect `ATTENTION` items
4. inspect `HOTSPOT` items
5. confirm manual owner for every unresolved blocking item

For pilot-wide review:

1. build `PILOT` launch visibility
2. review `blocked_deal_count`
3. review `overdue_count`
4. review `manual_review_count`
5. review the highest-severity items by `deal_id`

## Important Honesty Rule

This helper is a compensating control for Launch `L1`.

It must not be described as:

- full notification runtime
- full red-flag registry runtime
- full master dashboard runtime
- autonomous monitoring
- real-time alerting
