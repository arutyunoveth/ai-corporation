# Sprint DP3 — Real Tender Runbook and Redaction

## Scope

Create a safe operator runbook and tooling for using real or redacted tender materials during design-partner pilots.

This sprint prepares the workflow for real-world materials, but must not commit real sensitive customer data.

## Deliverables

1. Real tender data handling policy.
2. Redaction checklist template.
3. Expanded redaction workflow statuses and helpers.
4. Connection to DP1/DP2 access boundary and workspace.
5. Tests covering redaction workflow, export blocking, checklist generation.
6. Updated operator runbook, intake policy, and backlog.

## Redaction Workflow Statuses

- `raw_received` — material just arrived, not yet assessed
- `redaction_required` — operator marked for redaction
- `redaction_in_progress` — operator is actively redacting
- `redacted_for_internal_use` — redacted but not yet partner-safe
- `redacted_for_partner_report` — safe for partner export
- `blocked_sensitive` — cannot be used at all
- `approved_for_pilot_use` — cleared for pilot runs

## Acceptance Criteria

1. Raw sensitive intake cannot be used in partner export.
2. `blocked_sensitive` records are blocked.
3. Records `approved_for_pilot_use` can be used internally.
4. Records `redacted_for_partner_report` can be exported if visibility allows.
5. Redaction checklist generation works.
6. No real sensitive fixture data is required.

## Non-Goals

- No OCR or heavy document pipeline unless already existing and safe.
- No external document download.
- No storage of real partner data in repository.
- No production data-security implementation.
- No customer portal.
- No auto-redaction AI.

## Roadmap / Master Plan Alignment

- Current repository phase: `Design-Partner Pilot Stage`
- Sprint phase: `DP3 — Real Tender Runbook and Redaction`
- Master Plan section: `Create safe redaction workflow for real tender materials`
- Scope implemented: redaction workflow statuses, helpers, policy, checklist
- Explicit non-goals preserved: no auto-redaction AI, no external download, no production security
- Deferred items not touched: procurement integration, supplier automation, EDS/signature, SaaS hardening
- Tests proving alignment: targeted DP3 tests + DP1/DP2 tests + full pytest
- Docs updated: this sprint spec, Real_Tender_Data_Handling_Policy.md, Redaction_Checklist.md, Partner_Data_Intake_Policy.md, Operator_Runbook_MVP_v1.md, Product_Backlog.md
