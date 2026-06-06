# Pilot Evidence Ledger

## Purpose

`CP3` adds a structured internal evidence bundle for controlled commercial pilot runs. The ledger is artifact-based, repo-local, and intentionally lighter than production telemetry.

## What Gets Recorded

- `pilot_run_id`
- `scenario_id`
- `fixture_name`
- `deal_id`
- `provider_mode`
- UTC `started_at` / `ended_at`
- generated report references
- operator actions recorded through decision/event logs
- review notes
- blockers
- customer usefulness score
- estimated time saved
- final outcome

## Output Shape

Running the commercial MVP demo now produces:

- `{deal_id}_pilot_evidence.json`
- `{deal_id}_pilot_evidence.md`

These files are written next to the existing pre-bid and workspace reports.

## Boundaries

- internal evidence only
- no production telemetry pipeline
- no customer data ingestion
- no external reporting automation
- no submission or outbound communication

## Recommended Use

1. Run one pilot scenario at a time.
2. Keep provider mode explicit (`stub`, `deterministic`, or controlled `llm`).
3. Review the generated evidence bundle together with the report bundle.
4. Capture blockers and review notes before deciding whether the scenario is pilot-usable.
