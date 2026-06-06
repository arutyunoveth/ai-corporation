# Sprint DP6 — Design-Partner Dry Run

## Scope

Run an end-to-end design-partner pilot dry run using the new workspace, intake, redaction, export, and feedback loop.

This must still use synthetic or redacted data only.

## Deliverables

1. Dry-run script: `scripts/run_design_partner_pilot_dry_run.py`
2. Sample result doc.
3. Dry-run result template.
4. Tests covering end-to-end flow, boundary enforcement, no external actions.
5. Updated docs/backlog.

## Dry-Run Flow

1. Create partner workspace.
2. Create intake records (clean + sensitive).
3. Apply redaction statuses (redacted for partner, approved for pilot).
4. Prepare report sections with mixed visibility levels.
5. Generate export package with access guard and redaction rules.
6. Write Markdown + JSON outputs.
7. Approve for delivery.
8. Mark delivered manually.
9. Record feedback.
10. Record outcome.

## Acceptance Criteria

1. Script completes successfully.
2. Export package reaches at least `ready_for_review` or `delivered_manually`.
3. Feedback and outcome records are created.
4. Restricted/internal sections are omitted/blocked.
5. No external actions occur.
6. No DB or network dependency required.

## Non-Goals

- No real partner data.
- No network calls.
- No email.
- No procurement platform integration.
- No paid pilot execution.

## Roadmap / Master Plan Alignment

- Current repository phase: `Design-Partner Pilot Stage`
- Sprint phase: `DP6 — Design-Partner Dry Run`
- Master Plan section: `End-to-end design-partner pilot dry run`
- Scope implemented: dry-run script, sample result, template, tests
- Explicit non-goals preserved: no real data, no network, no email, no procurement
- Deferred items not touched: procurement integration, supplier automation, EDS/signature, SaaS hardening
- Tests proving alignment: targeted DP6 tests + DP1-DP5 tests + full pytest
- Docs updated: this sprint spec, sample result, dry-run template, Product_Backlog.md
