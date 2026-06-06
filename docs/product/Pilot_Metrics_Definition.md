# Pilot Metrics Definition

## Purpose

This document defines the minimum metrics attached to each controlled commercial pilot evidence bundle.

## Required Fields

### Run Identity

- `pilot_run_id`
- `scenario_id`
- `fixture_name`
- `deal_id`
- `provider_mode`

### Timing

- `started_at` (UTC)
- `ended_at` (UTC)

### Artifact References

- pre-bid report markdown/json
- workspace report markdown/json
- summary json

### Workflow Evidence

- operator action count
- blocker count
- generated report count
- operator action history from decision/event records
- review notes

### Commercial Value Signals

- `customer_usefulness_score` on a 1..5 scale
- `estimated_time_saved_minutes`
- `final_outcome`

## Interpretation Rules

- `customer_usefulness_score` is an internal operator-assessed proxy unless real pilot feedback is explicitly collected.
- `estimated_time_saved_minutes` is directional and must not be presented as audited ROI.
- `final_outcome` remains internal and human-reviewed.
- any blocker with `high` or `critical` severity prevents treating the scenario as pilot-ready evidence.

## Non-Goals

- no analytics dashboard
- no live telemetry
- no auto-export to customer systems
- no automated customer satisfaction collection
