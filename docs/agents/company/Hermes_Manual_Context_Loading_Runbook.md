# Hermes Manual Context Loading Runbook

## Purpose

This runbook explains how to manually load Arvectum company agent context into Hermes.

## Current boundary

ai-corporation is a context provider only.

It does not:
- call LLMs;
- execute prompts;
- run agents;
- dispatch to cloud;
- perform autonomous workflows.

## Export manifest

```bash
python -m scripts.export_hermes_company_manifest
python -m scripts.export_hermes_company_manifest --output tmp/hermes_company_manifest.json
```

## Export agent context

```bash
# Markdown format (default)
python -m scripts.export_company_agent_context --agent-id A00
python -m scripts.export_company_agent_context --agent-id A10 --output tmp/A10_context.md

# JSON format
python -m scripts.export_company_agent_context --agent-id A00 --format json
python -m scripts.export_company_agent_context --agent-id A21 --format json --output tmp/A21_context.json

# With metadata
python -m scripts.export_company_agent_context --agent-id A00 --include-metadata
python -m scripts.export_company_agent_context --agent-id A00 --format json --include-metadata
```

## Export workflow route

```bash
python -m scripts.export_company_workflow_route --route-id company_tender_bid_no_bid
python -m scripts.export_company_workflow_route --route-id company_tender_bid_no_bid --output tmp/route.json
```

## Recommended local runtime

Use sequential execution.

```text
max_parallel_local_agents = 1
```

## Recommended Hermes flow

```text
CEO instruction
→ load A00 Chief of Staff context
→ A00 selects route
→ export specialist agent context
→ run specialist in Hermes
→ save artifact manually
→ CEO decision
```

## Local-only data

Never send to cloud models:

* tender documents;
* supplier quotes;
* TKP;
* contracts;
* financial models;
* source code;
* secrets;
* server configs;
* production logs;
* private client notes.

## Available routes

| Route | Owner | Supporting | Final Artifact |
|-------|-------|------------|----------------|
| company_tender_bid_no_bid | A10 | A11, A20, A21, A42 | CEO Decision Memo |
| company_architecture_review | A40 | A42 | Architecture Decision Record |
| company_release_readiness | A42 | A40 | QA Readiness Memo |
| company_marketing_asset_review | A51 | A52 | Marketing Asset Approval Memo |
| company_sales_lead_qualification | A50 | A20, A21 | Lead Qualification Memo |
