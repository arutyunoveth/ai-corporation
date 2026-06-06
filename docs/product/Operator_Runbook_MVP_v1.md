# Operator Runbook MVP v1

## Primary Demo Command

```bash
.venv/bin/python scripts/run_commercial_mvp_v1_demo.py --provider stub --output-dir tmp/commercial_mvp_v1_demo
```

## Manual Operator Flow

1. Run the commercial pre-bid demo or ingest an equivalent test tender.
   - state: `imported`
2. Review:
   - pre-bid report
   - requirements
   - risks
   - runtime trace metadata
   - state after successful analysis: `analyzed`
3. If the analysis is incomplete, record `needs_more_review` in the operator console.
   - state: `needs_review`
4. If supplier input is required, record `collect_tkp` in the operator console.
   - state: `collect_tkp`
5. Generate supplier request draft:
   - `POST /commercial-workspace/{deal_id}/supplier-request-draft`
6. Register manual TKP batch:
   - `POST /commercial-workspace/{deal_id}/tkp/register-manual-batch`
7. Record `tkp_received` in the commercial workspace after manual quote inputs are complete.
8. Build readiness:
   - `POST /commercial-workspace/{deal_id}/readiness/build`
   - state: `economics_review` then `bid_readiness_review`
9. Review:
   - quote comparison
   - finance memo
   - bid completeness
   - submission readiness
10. Record `economics_reviewed` if the internal package is explainable and complete.
11. Record final internal action:
   - `POST /commercial-workspace/{deal_id}/actions`
   - allowed terminal state in-repo: `ready_for_human_submission`

## Access Boundary

All pilot artifacts are classified under a visibility level. See `Pilot_Access_Boundary_Policy.md` for full rules. Key defaults:

- runtime traces are `internal_only` — not visible to partners
- operator decisions/actions are `operator_visible` — not exportable
- pilot evidence and metrics are `partner_visible` — may be shared
- customer reports after human review are `exportable_to_partner`
- sensitive notes are `restricted_sensitive` — admin only

Always run the export guard before delivering artifacts to a design partner.

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
- operator decisions and events for every internal control gate
