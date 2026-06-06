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

## Partner Report Export

See `Partner_Report_Export_Policy.md` and `Manual_Delivery_Checklist.md` for full rules.

1. Generate package: `generate_export_package(partner_workspace_id=..., scenario_or_tender_id=..., report_sections=...)`.
2. Review the package — check included, redacted, and blocked sections.
3. If acceptable: `approve_for_delivery()`.
4. Deliver manually outside the repository.
5. Record delivery: `mark_delivered_manually()`.
6. Never send automated email. Never upload automatically.

## Redaction Workflow

See `Real_Tender_Data_Handling_Policy.md` and `Redaction_Checklist.md` for full rules.

1. Raw materials arrive as `raw_received`.
2. Mark records needing redaction: `require_redaction()`.
3. Redact manually, then `mark_redacted_for_internal()` or `mark_redacted_for_partner()`.
4. If too sensitive: `block_sensitive()`.
5. Before any pilot run: run `generate_redaction_checklist()`.
6. Check `can_use_in_pilot_run()` and `can_appear_in_partner_report()` before using records.

Never commit real customer/partner data. Use synthetic or redacted fixtures.

## Partner Workspace

Every design partner engagement uses a workspace. See `Partner_Data_Intake_Policy.md` for full rules.

1. Create workspace: `create_workspace(partner_label=..., created_by=...)`
2. Add intake records: `add_intake_record(partner_workspace_id=..., source_type=..., source_label=...)`
3. Classify visibility: automatic via `classify_default_visibility()`
4. Check readiness: `check_export_readiness()` before partner-facing use
5. List partner-visible artifacts: `list_partner_visible_artifacts()` excludes internal/restricted records

Important: never commit real customer/partner data. Use `synthetic` or `redacted_real` intake modes.

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
