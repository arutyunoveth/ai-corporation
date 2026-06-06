# Local Pilot Folder Template

Use this folder structure for each partner tender in a restricted paid pilot run.

## Structure

```
local_pilot_runs/<partner_label>/
  partner_profile.md                    # Partner company profile (local only, not committed)
  <tender_label>/
    01_raw_docs/                        # Original tender documents (gitignored)
      notice.pdf                        # Tender notice (example)
      technical_specification.pdf       # Technical specification (example)
      draft_contract.pdf                # Contract draft (example)
    02_extracted_text/                  # Text extracts for analysis
      notice.txt                        # Notice text
      technical_spec.txt                # Technical specification text
      contract_draft.txt                # Contract draft text
    03_operator_notes/                  # Operator notes (local only)
      intake_notes.txt
    04_system_output/                   # System-generated analysis outputs
      run_summary.json                  # Summary of the pilot run
      internal_analysis.md              # Full internal analysis report
    05_partner_export/                  # Partner-facing export package
      partner_report.md                 # Redacted partner report
      export_summary.json               # Export package summary
    06_feedback/                        # Feedback and outcome records
      feedback_notes.md                 # Feedback collection notes
      outcome_record.md                 # Outcome decision record
```

## Rules

- `01_raw_docs/`, `03_operator_notes/`, and `partner_profile.md` are for local use only.
- Do not commit `01_raw_docs/`, `03_operator_notes/`, or `partner_profile.md`.
- `02_extracted_text/` may be committed only after redaction review.
- `04_system_output/` contains internal analysis — commit only if no sensitive data.
- `05_partner_export/` contains partner-ready output — may be committed after delivery.
- `06_feedback/` contains anonymized feedback — may be committed.

## Creating a New Pilot Folder

```bash
# Replace <partner_label> and <tender_label> with actual values
mkdir -p local_pilot_runs/<partner_label>/<tender_label>/01_raw_docs
mkdir -p local_pilot_runs/<partner_label>/<tender_label>/02_extracted_text
mkdir -p local_pilot_runs/<partner_label>/<tender_label>/03_operator_notes
mkdir -p local_pilot_runs/<partner_label>/<tender_label>/04_system_output
mkdir -p local_pilot_runs/<partner_label>/<tender_label>/05_partner_export
mkdir -p local_pilot_runs/<partner_label>/<tender_label>/06_feedback
```
