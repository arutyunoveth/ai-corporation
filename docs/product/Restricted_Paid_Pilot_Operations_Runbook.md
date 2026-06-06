# Restricted Paid Pilot Operations Runbook

## Purpose

This runbook describes how to run a restricted paid/design-partner pilot operation using the repository tooling while respecting all manual-control and access-boundary restrictions.

## Prerequisites

- Repository is cloned and dependencies installed (`pip install -e .[dev]`).
- PostgreSQL is running and Alembic migrations are applied (`alembic upgrade head`).
- Virtual environment is activated.
- The operator has read the following policies:
  - `Pilot_Access_Boundary_Policy.md`
  - `Partner_Data_Intake_Policy.md`
  - `Real_Tender_Data_Handling_Policy.md`
  - `Partner_Report_Export_Policy.md`
  - `Local_Pilot_Data_Handling_Policy.md`

## Pilot Flow

### 1. Select Partner and Confirm Scope

1. Identify a partner who accepts manual-control restrictions.
2. Confirm they understand the limitations (see `Pilot_Limitations_Disclosure.md`).
3. Collect company profile into a local-only file (not committed).
4. Agree on tender scope and expected outputs.

### 2. Collect Tender Materials

1. Receive tender documents from partner via external channel (email, portal).
2. Save to `local_pilot_runs/<partner_label>/raw/` — this directory is gitignored.
3. Create intake records using `add_intake_record()` from `partner_workspace`.
4. Mark records with `contains_sensitive_data` and `redaction_status` as appropriate.

### 3. Redact Sensitive Data

1. Use `Redaction_Checklist.md` to guide the process.
2. For each sensitive record:
   - If redactable: `mark_redacted_for_partner()` or `mark_redacted_for_internal()`.
   - If too sensitive: `block_sensitive()`.
   - If no redaction needed: `approve_for_pilot_use()`.
3. Run `generate_redaction_checklist()` to verify all records.

### 4. Run Analysis

1. Use existing demo/analysis scripts:
   - `scripts/run_commercial_mvp_v1_demo.py` for pre-bid analysis.
   - `scripts/run_design_partner_pilot_dry_run.py` for a full dry run.
2. Or use the commercial operator console endpoints for manual analysis.
3. All analysis outputs go to `tmp/` or `local_pilot_runs/<partner_label>/output/`.

### 5. Generate Export Package

1. Prepare report sections from analysis outputs.
2. Call `generate_export_package()` to create the export package.
3. Review the package — check included, redacted, and blocked sections.
4. If blocked sections exist, resolve before proceeding.

### 6. Review Manually

1. Review the full export package:
   - Is all restricted_sensitive data blocked?
   - Is all internal_only data redacted?
   - Is all operator_visible data omitted?
   - Are partner-visible sections accurate?
2. If satisfactory, call `approve_for_delivery()`.

### 7. Deliver Manually

1. Use the export markdown/json output from `render_export_markdown()` / `render_export_json()`.
2. Deliver to partner via external channel (email, secure portal).
3. Call `mark_delivered_manually()` to record delivery.
4. Follow `Manual_Delivery_Checklist.md`.

### 8. Collect Feedback

1. Schedule a call or send the `Design_Partner_Feedback_Form.md`.
2. Record feedback using `create_feedback()`.
3. Capture usefulness, clarity, trust scores and would-pay signal.

### 9. Record Outcome

1. Review feedback and decide next action.
2. Record outcome using `create_outcome()`.
3. Choose final decision: continue, offer paid pilot, pause, or stop.

### 10. Decide Next Step

1. Based on outcome, choose next action:
   - `iterate_report` → repeat pilot cycle with improved outputs.
   - `revise_workflow` → update internal tooling.
   - `request_more_data` → collect additional tender materials.
   - `prepare_paid_pilot_offer` → initiate paid pilot proposal.
   - `pause_partner` → pause engagement.
   - `reject_use_case` → end engagement.

## Safety Rules

- Never commit real partner data to the repository.
- Never send automated email or external messages from the repository.
- Never attempt procurement platform login, upload, or submission.
- Never treat `ready_for_human_submission` as actual submission.
- Never bypass the export guard.
- Always get human review before delivery.

## Troubleshooting

- **Export blocked**: Check `blocked_sections`. Resolve sensitive content or mark as blocked_sensitive.
- **Intake record not visible**: Check visibility level and redaction status. Run `can_use_in_pilot_run()` and `can_appear_in_partner_report()`.
- **Script fails**: Ensure DB is running, Alembic is up to date, and virtual environment is activated.
