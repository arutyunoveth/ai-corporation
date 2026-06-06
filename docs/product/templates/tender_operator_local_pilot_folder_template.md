# Tender Operator Local Pilot Folder Template

Use this folder structure for each tender operator pilot run.

## Structure

```
local_pilot_runs/<operator_label>/
  operator_profile.md                  # Tender-operator constraints and preferences (local only)
  <tender_label>/
    01_raw_docs/                        # Original tender documents (gitignored)
      notice.pdf                        # Tender notice (example)
      technical_specification.pdf       # Technical specification (example)
      draft_contract.pdf                # Contract draft (example)
    02_extracted_text/                  # Text extracts for analysis
      notice.txt                        # Notice text (required)
      technical_spec.txt                # Technical specification text (required)
      contract_draft.txt                # Contract draft text (required)
    03_supplier_search/                 # Supplier research and RFQ tracking
      supplier_candidates.md            # Potential supplier list (optional)
      rfq_draft.md                      # Generated RFQ/TKP request draft
    04_tkp/                             # TKP/commercial offers from suppliers (optional)
      supplier_001_tkp.md               # TKP from supplier 001
      supplier_002_tkp.md               # TKP from supplier 002
    05_system_output/                   # System-generated analysis outputs
      run_summary.json                  # Summary of the pilot run
      internal_operator_analysis.md     # Full internal operator analysis
      requirements.json                 # Extracted requirements
      supplier_questions.json           # Supplier question list for RFQ
      rfq_request_draft.md              # RFQ/TKP request draft
      calibrated_contract_risk_memo.md  # Three-tier contract risk assessment
      tkp_comparison.json               # TKP comparison (if TKPs exist)
      economics_summary.json            # Economics calculation (if TKPs exist)
      bid_decision_recommendation.md    # Bid decision recommendation (if TKPs exist)
    06_partner_export/                  # Partner-facing export package
      operator_report.md                # Redacted operator report
      export_summary.json               # Export package summary
    07_feedback/                        # Feedback and outcome records
      feedback_notes.md                 # Feedback collection notes
      outcome_record.md                 # Outcome decision record
```

## Rules

- `01_raw_docs/`, `03_supplier_search/`, and `operator_profile.md` are for local use only.
- Do not commit `01_raw_docs/`, `03_supplier_search/` with raw supplier data, or `operator_profile.md`.
- `02_extracted_text/` may be committed only after redaction review.
- `04_tkp/` contains real supplier offers — do not commit without redaction.
- `05_system_output/` contains internal analysis — commit only if no sensitive data.
- `06_partner_export/` contains partner-ready output — may be committed after delivery.
- `07_feedback/` contains anonymized feedback — may be committed.

## Creating a New Pilot Folder

```bash
# Replace <operator_label> and <tender_label> with actual values
mkdir -p local_pilot_runs/<operator_label>/<tender_label>/{01_raw_docs,02_extracted_text,03_supplier_search,04_tkp,05_system_output,06_partner_export,07_feedback}
```
