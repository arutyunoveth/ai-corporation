# Tender Operator Pilot Runbook

## Purpose

This runbook explains how to use `scripts/run_tender_operator_pilot.py` to process a real tender for a tender/operator company from a local folder.

The runner supports an RFQ-first workflow: requirement extraction → supplier questions → RFQ draft → TKP collection → TKP comparison → economics → bid decision.

## Prerequisites

- Repository is cloned and dependencies installed.
- Virtual environment is activated.
- You have read:
  - `Local_Pilot_Data_Handling_Policy.md`
  - `Restricted_Paid_Pilot_Operations_Runbook.md`
  - `Redaction_Checklist.md`
  - `Calibrated_Contract_Risk_Method.md`
  - `Tender_Operator_RFQ_Workflow.md`

## Step 1: Create Local Folder

Create the folder structure for the tender operator:

```bash
mkdir -p local_pilot_runs/<operator_label>/<tender_label>/{01_raw_docs,02_extracted_text,03_supplier_search,04_tkp,05_system_output,06_partner_export,07_feedback}
```

## Step 2: Place Documents

1. Download tender documents from the procurement portal (email, ETP, etc.).
2. Save original documents (PDF, DOCX, etc.) to `01_raw_docs/`.
3. Create plain text extracts in `02_extracted_text/` with these required files:
   - `notice.txt` — The tender notice / announcement text.
   - `technical_spec.txt` — The technical specification text.
   - `contract_draft.txt` — The contract draft text.

## Step 3: (Optional) Create Operator Profile

Create `local_pilot_runs/<operator_label>/operator_profile.md` using the `Tender_Operator_Profile_Template.md`. This describes:
- Working categories (not a product catalog)
- Excluded categories
- Regions
- NMCK range
- VAT mode
- Target margin
- Acceptable payment delay / contract security
- License/SRO information
- Supplier search preferences

No product prices or fixed SKUs are required.

## Step 4: (Optional) Search for Suppliers

Add supplier candidates to `03_supplier_search/supplier_candidates.md`. This is manual.

The system does not perform automatic internet search.

## Step 5: Run the Command

```bash
.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider stub \
  --output-dir local_pilot_runs/tender_operator_001/tender_001/05_system_output
```

### Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--operator-id` | Yes | — | Operator identifier (used for workspace creation) |
| `--tender-dir` | Yes | — | Path to the tender folder containing `02_extracted_text/` |
| `--provider` | Yes | — | Analysis provider: `stub` (always works) or `llm` (requires DB + API key) |
| `--output-dir` | No | `<tender-dir>/05_system_output` | Where to write system output files |

### Provider Choices

- **`stub`** (recommended for testing): Uses canned synthetic analysis. No external dependencies.
- **`llm`**: Attempts to use the controlled LLM pre-bid analysis module. Requires:
  - PostgreSQL database running with Alembic migrations applied.
  - `AI_CORP_OPENAI_API_KEY` environment variable set.
  - Falls back gracefully with a warning if unavailable.

## Step 6: Review Outputs (Before TKP)

If no TKP files are present in `04_tkp/`, the run stops at `rfq_ready` / `collect_tkp`.

| File | Location | Content | Can Send? |
|---|---|---|---|
| `run_summary.json` | `05_system_output/` | JSON run summary | No |
| `internal_operator_analysis.md` | `05_system_output/` | Full internal analysis | No |
| `requirements.json` | `05_system_output/` | Extracted tender requirements | No |
| `supplier_questions.json` | `05_system_output/` | Supplier questions for RFQ | Yes (anonymized) |
| `rfq_request_draft.md` | `05_system_output/` | RFQ/TKP request draft | Yes (for sending) |
| `calibrated_contract_risk_memo.md` | `05_system_output/` | Three-tier risk assessment | No |
| `operator_report.md` | `06_partner_export/` | Partner-facing report | Yes (after review) |
| `export_summary.json` | `06_partner_export/` | Export metadata | No |

## Step 7: Send RFQ and Collect TKP

1. Review `rfq_request_draft.md` and `supplier_questions.json`.
2. Customize for each supplier candidate.
3. Send manually via external channel (email, portal).
4. When suppliers respond, save each TKP to `04_tkp/`.

## Step 8: Re-run with TKP

If TKP files exist in `04_tkp/`, the runner generates additional outputs:

| File | Location | Content |
|---|---|---|
| `tkp_comparison.json` | `05_system_output/` | Side-by-side TKP comparison |
| `economics_summary.json` | `05_system_output/` | Cost calculation and margin analysis |
| `bid_decision_recommendation.md` | `05_system_output/` | Preliminary bid decision |

## Step 9: Manual Review and Delivery

1. Review `06_partner_export/operator_report.md`.
2. Verify no restricted or internal data is exposed.
3. Deliver manually via external channel.

## Step 10: Collect Feedback

1. Use `Tender_Operator_Profile_Template.md` or `Partner_Feedback_Template.md`.
2. Save to `07_feedback/`.

## Important Rules

- **Never commit raw tender documents.** `01_raw_docs/` is gitignored.
- **Never commit real TKP data without redaction.**
- **Only `06_partner_export/operator_report.md` is partner-ready.**
- **Do not send internal analysis files to partners.**
- **Final bid submission remains fully manual.**
- **No automated external communication is generated by this script.**

## Migration Note for Old PP1 Users

If you previously used `scripts/run_partner_tender_folder.py` (old PP1) with product-catalog partners:

1. The old script is still available for backward compatibility.
2. For tender-operator customers, use the new `run_tender_operator_pilot.py`.
3. The folder structure has changed:
   - Old: `04_system_output/`, `05_partner_export/`, `06_feedback/`
   - New: `05_system_output/`, `06_partner_export/`, `07_feedback/` (with new folders `03_supplier_search/`, `04_tkp/`)
4. Output files are more comprehensive in the new runner.
