# Company Agent Dry Run 0

## Scenario

Assess Arvectum readiness for first paid restricted tender-operations pilot.

## Boundary

This dry run is manual.

ai-corporation does not:
- call LLMs;
- execute prompts;
- run agents;
- dispatch to cloud;
- perform autonomous workflow steps.

## Route

1. Export A00 context.
2. Run A00 manually in Hermes.
3. Save A00 routing memo manually.
4. Export A10, A20, A21, A42 contexts.
5. Run each specialist manually in Hermes, sequentially.
6. Save specialist artifacts manually.
7. Run A00 final synthesis manually.
8. Save CEO Decision Memo.

## Required commands

```bash
python -m scripts.export_hermes_company_manifest --output tmp/hermes_company_manifest.json

python -m scripts.export_company_workflow_route --route-id company_pilot_readiness_review --output tmp/company_pilot_readiness_review.json

python -m scripts.export_company_agent_context --agent-id A00 --output tmp/A00_context.md
python -m scripts.export_company_agent_context --agent-id A10 --output tmp/A10_context.md
python -m scripts.export_company_agent_context --agent-id A20 --output tmp/A20_context.md
python -m scripts.export_company_agent_context --agent-id A21 --output tmp/A21_context.md
python -m scripts.export_company_agent_context --agent-id A42 --output tmp/A42_context.md
```

## Expected artifacts

```text
artifacts/A00_routing_memo.md
artifacts/A10_tender_operations_readiness.md
artifacts/A20_finance_readiness.md
artifacts/A21_legal_risk_readiness.md
artifacts/A42_qa_release_readiness.md
artifacts/A00_final_synthesis.md
final/ceo_decision_memo.md
```
