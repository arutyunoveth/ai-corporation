# Company Agents Metadata Extension

This change extends the existing bounded M-049/M-050/M-051 metadata-control slice to describe Arvectum internal company operations agents.

## What this adds

- company_operations agent scope;
- internal company agent metadata;
- Hermes-compatible manual context assets;
- sequential execution policy;
- company workflow metadata;
- context exporter for manual Hermes usage.

## What this does not add

This change does not introduce:

- autonomous execution;
- prompt execution runtime;
- cloud dispatch;
- external Hermes server integration;
- self-serve agent runtime;
- new canonical modules;
- unattended decision-making.

## Boundary

All company agents are advisory/manual-context roles.

CEO approval is required for:
- money;
- contracts;
- client promises;
- production deployment;
- legal responsibility;
- external communication;
- confidential data boundary changes.
