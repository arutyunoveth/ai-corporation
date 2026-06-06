# Sprint DP2 — Partner Workspace and Data Intake

## Scope

Create a bounded design-partner workspace and safe data intake layer for pilot usage.

This is not production multi-tenancy and not production auth.
This is a pilot-safe workspace model so internal operators can organize partner-provided tender materials without leaking internal artifacts.

## Deliverables

1. Partner workspace schemas: `partner_workspace_id`, `partner_label`, `partner_stage`, `allowed_artifact_visibility`, `intake_mode`, `data_handling_notes`, `created_by`, `review_status`, `created_at`.
2. Intake record schemas: `intake_record_id`, `partner_workspace_id`, `source_type`, `source_label`, `contains_sensitive_data`, `redaction_status`, `visibility_level`, `operator_notes`, `linked_tender_or_scenario_id`, `created_at`.
3. Service helpers: `create_workspace`, `add_intake_record`, `classify_default_visibility`, `check_export_readiness`, `list_partner_visible_artifacts`, `block_restricted_from_export`.
4. DP1 access boundary applied: workspace metadata defaults to `operator_visible`, partner-safe to `partner_visible`, sensitive notes to `restricted_sensitive`.
5. Docs: sprint spec, partner data intake policy.
6. Tests: workspace creation, intake records, visibility, export guard, partner-visible listing.
7. Updated operator runbook and backlog.

## Partner Stages

- `draft`, `active_design_partner`, `paused`, `completed`, `archived`

## Intake Modes

- `synthetic`, `redacted_real`, `manual_entry`, `operator_uploaded`, `external_reference_only`

## Source Types

- `tender_link`, `notice_text`, `technical_spec_text`, `contract_draft_text`, `quote_file_summary`, `manual_notes`, `other`

## Redaction Statuses

- `not_required`, `pending_redaction`, `redacted`, `blocked_sensitive`, `needs_review`

## Default Visibility Rules

- workspace metadata: `operator_visible`
- partner-safe scenario metadata: `partner_visible`
- source documents / tender texts: `operator_visible` unless explicitly marked `exportable_to_partner`
- sensitive notes: `restricted_sensitive`
- internal traces: `internal_only`

## Acceptance Criteria

1. Workspace and intake records can be created.
2. Default visibility is classified correctly based on sensitivity and redaction status.
3. `design_partner_viewer` cannot view internal/restricted intake records.
4. Export guard blocks sensitive/restricted intake.
5. Partner-visible list excludes internal traces and restricted notes.
6. All existing DP1 access boundary tests and full suite still pass.

## Non-Goals

- No production auth.
- No login/session.
- No real tenant isolation.
- No file upload security layer beyond pilot metadata.
- No external procurement platform fetch.
- No real external data scraping.
- No supplier communication.
- No customer portal.

## Roadmap / Master Plan Alignment

- Current repository phase: `Design-Partner Pilot Stage`
- Sprint phase: `DP2 — Partner Workspace and Data Intake`
- Master Plan section: `Create bounded partner workspace and safe data intake layer`
- Scope implemented: partner workspace schema, intake record schema, service helpers, access boundary enforcement
- Explicit non-goals preserved: no production auth, no tenant isolation, no platform integration
- Deferred items not touched: procurement integration, supplier automation, EDS/signature, SaaS hardening, broad autonomy
- Tests proving alignment: targeted DP2 tests + DP1 boundary tests + full pytest
- Docs updated: this sprint spec, Partner_Data_Intake_Policy.md, Operator_Runbook_MVP_v1.md, Product_Backlog.md
