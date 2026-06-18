# Company Agent Runtime Policy

Arvectum company agents are designed for sequential execution, not parallel swarm execution.

## Default local execution limit

max_parallel_local_agents = 1

## Reason

The target local runtime machine is Mac mini M4 Pro with 24 GB RAM.

Agent is not a separate model.

Agent is:
- role;
- metadata;
- identity context;
- behavioral profile;
- policy;
- artifact contract.

The same local model may be reused for multiple agents by loading a different agent context.

## Local-only data

Never send to cloud models:

- tender documents;
- supplier quotes;
- TKP;
- contracts;
- financial models;
- source code;
- secrets;
- server configs;
- production logs;
- private client notes;
- private CRM notes.

## Cloud-allowed data

Cloud models may be used only for:

- public website copy;
- generic marketing drafts;
- anonymized product ideas;
- public research;
- non-confidential templates.

## Default rule

If unsure, use local model.

## Runtime boundary

This phase does not implement:
- autonomous execution;
- prompt execution runtime;
- cloud dispatch;
- external Hermes server integration;
- self-serve agent runtime.
