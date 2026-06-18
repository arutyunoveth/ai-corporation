# Company Agents Production Hardening

## What changed

- Alembic migration `087_add_company_agent_metadata_fields` added for company agent metadata fields.
- Company agent metadata is now production-schema ready.
- Context exporter remains manual and local.
- Runtime execution remains deferred.

## Migration details

Revision: `087_add_company_agent_metadata_fields`
Revises: `086_create_runtime_metadata_slices`

### Columns added to `agent_registry_records`

| Column | Type | Nullable | Default |
|--------|------|----------|---------|
| agent_scope | String(64) | YES | - |
| agent_kind | String(64) | YES | - |
| reports_to | String(128) | YES | - |
| data_policy | String(64) | YES | - |
| runtime_mode | String(64) | YES | - |
| model_tier | String(64) | YES | - |
| description | Text | YES | - |
| responsibilities_json | JSON | NO | [] |
| inputs_json | JSON | NO | [] |
| outputs_json | JSON | NO | [] |
| escalation_rules_json | JSON | NO | [] |
| forbidden_actions_json | JSON | NO | [] |

### Index added

- `ix_agent_registry_records_agent_scope` on `agent_registry_records(agent_scope)`

### Downgrade

All columns and index are dropped in downgrade.

## What this does not change

This sprint does not introduce:
- autonomous execution;
- prompt execution runtime;
- cloud dispatch;
- external Hermes server integration;
- self-serve agent runtime;
- unattended decision-making.

## Current status

Company agents are ready as bounded metadata/manual-context records.

Hermes integration remains a future phase.

## Hermes manual integration status

Company agents can now be exported as Hermes-compatible manual context bundles.

This does not open:
- prompt execution runtime;
- autonomous agent execution;
- cloud dispatch;
- external side effects.

## Dry Run 0

The first recommended manual operating-loop validation is:

```text
company_pilot_readiness_review
```

This route validates whether Arvectum is ready for the first paid restricted tender-operations pilot.

This dry run remains manual and sequential.

See: `company_agent_runs/dry_run_0/README.md`
