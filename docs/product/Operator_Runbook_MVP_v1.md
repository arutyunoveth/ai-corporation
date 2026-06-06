# Operator Runbook MVP v1

## Primary Demo Command

```bash
.venv/bin/python scripts/run_commercial_mvp_v1_demo.py --provider stub --output-dir tmp/commercial_mvp_v1_demo
```

## Manual Operator Flow

1. Run the commercial pre-bid demo or ingest an equivalent test tender.
2. Review:
   - pre-bid report
   - requirements
   - risks
   - runtime trace metadata
3. Generate supplier request draft:
   - `POST /commercial-workspace/{deal_id}/supplier-request-draft`
4. Register manual TKP batch:
   - `POST /commercial-workspace/{deal_id}/tkp/register-manual-batch`
5. Build readiness:
   - `POST /commercial-workspace/{deal_id}/readiness/build`
6. Review:
   - quote comparison
   - finance memo
   - bid completeness
   - submission readiness
7. Record final internal action:
   - `POST /commercial-workspace/{deal_id}/actions`

## Mandatory Control Rules

- never treat `ready_for_human_submission` as actual submission
- final submission remains manual
- never send supplier email automatically from the repository
- never approve final commercial/legal decisions without a human
- keep provider-backed LLM output under schema validation and human review

## Expected Outputs

- pre-bid report markdown/json
- workspace report markdown/json
- finance and readiness identifiers for audit traceability
