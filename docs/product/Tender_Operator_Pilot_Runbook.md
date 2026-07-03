# Tender Operator Pilot Runbook

## Purpose

This runbook explains how to manually run the Tender Operator pilot with
`scripts/run_tender_operator_pilot.py`.

The workflow is RFQ-first:

1. load tender documents
2. extract requirements
3. generate supplier questions
4. generate RFQ draft
5. manually collect TKP/commercial offers
6. re-run to build TKP comparison, economics, and bid recommendation

This is a **manual-control** workflow. No automated external communication,
portal submission, or supplier outreach is performed by the repository.

## Read First

Before using the runner, read:

- `Local_Pilot_Data_Handling_Policy.md`
- `Restricted_Paid_Pilot_Operations_Runbook.md`
- `Redaction_Checklist.md`
- `Calibrated_Contract_Risk_Method.md`
- `Tender_Operator_RFQ_Workflow.md`
- `Partner_Report_Export_Policy.md`

## Verified State

The `stub` workflow in this runbook was verified locally on `2026-07-02`
against the synthetic fixture copied from:

- `tests/fixtures/local_pilot_runs/tender_operator_001`

Verified outcomes:

- first run without TKP finishes with `pilot_status=rfq_ready_collect_tkp`
- second run with TKP finishes with `pilot_status=tkp_received_economics_ready`
- partner export files are written to `06_partner_export/`
- system output files are written to `05_system_output/`

## Preconditions

- Repository is cloned.
- Virtual environment exists.
- Dependencies are installed.
- You will run from the repository root.
- Real tender files stay in ignored local folders only.

Recommended setup:

```bash
python3 -m venv .venv
.venv/bin/pip install -e .[dev]
```

Quick preflight:

```bash
.venv/bin/python --version
.venv/bin/python scripts/run_tender_operator_pilot.py --help
```

## Folder Structure

Create this structure for each operator and tender:

```bash
mkdir -p local_pilot_runs/<operator_label>/<tender_label>/{01_raw_docs,02_extracted_text,03_supplier_search,04_tkp,05_system_output,06_partner_export,07_feedback}
```

Expected layout:

```text
local_pilot_runs/<operator_label>/
  operator_profile.md
  <tender_label>/
    01_raw_docs/
    02_extracted_text/
      notice.txt
      technical_spec.txt
      contract_draft.txt
    03_supplier_search/
      supplier_candidates.md
    04_tkp/
    05_system_output/
    06_partner_export/
    07_feedback/
```

Important:

- `01_raw_docs/` is for original files only and must never be committed.
- `04_tkp/` contains real supplier offers and must never be committed without redaction.
- `05_system_output/` is internal.
- `06_partner_export/operator_report.md` is the only partner-facing file produced by this runner.

## Optional Smoke Check

Run this once before a real pilot to confirm the environment works.

Copy the synthetic fixture to a throwaway folder:

```bash
rm -rf tmp/manual_pilot_smoke
mkdir -p tmp/manual_pilot_smoke
cp -R tests/fixtures/local_pilot_runs/tender_operator_001 tmp/manual_pilot_smoke/
```

Run the verified `stub` scenario:

```bash
.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir tmp/manual_pilot_smoke/tender_operator_001/tender_001 \
  --provider stub \
  --output-dir tmp/manual_pilot_smoke/tender_operator_001/tender_001/05_system_output
```

Expected result:

- exit code `0`
- output includes `PP1R Run Complete`
- `run_summary.json` exists
- `pilot_status` is `tkp_received_economics_ready` for the fixture with TKP

To verify the first-pass RFQ state, repeat the smoke check without TKP files:

```bash
rm -rf tmp/manual_pilot_no_tkp
mkdir -p tmp/manual_pilot_no_tkp
cp -R tests/fixtures/local_pilot_runs/tender_operator_001 tmp/manual_pilot_no_tkp/
rm -f tmp/manual_pilot_no_tkp/tender_operator_001/tender_001/04_tkp/*

.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir tmp/manual_pilot_no_tkp/tender_operator_001/tender_001 \
  --provider stub \
  --output-dir tmp/manual_pilot_no_tkp/tender_operator_001/tender_001/05_system_output
```

Expected result:

- exit code `0`
- `pilot_status` is `rfq_ready_collect_tkp`
- no `tkp_comparison.json`
- no `economics_summary.json`
- no `bid_decision_recommendation.md`

## Real Pilot Procedure

## Step 1: Create the Local Pilot Folder

```bash
mkdir -p local_pilot_runs/<operator_label>/<tender_label>/{01_raw_docs,02_extracted_text,03_supplier_search,04_tkp,05_system_output,06_partner_export,07_feedback}
```

Example:

```bash
mkdir -p local_pilot_runs/tender_operator_001/tender_001/{01_raw_docs,02_extracted_text,03_supplier_search,04_tkp,05_system_output,06_partner_export,07_feedback}
```

## Step 2: Save Source Documents

Put original files into:

- `01_raw_docs/notice.*`
- `01_raw_docs/technical_specification.*`
- `01_raw_docs/draft_contract.*`

These raw files are for local operator use only.

## Step 3: Prepare Extracted Text

Create these required text files in `02_extracted_text/`:

- `notice.txt`
- `technical_spec.txt`
- `contract_draft.txt`

The script fails immediately if any of these files is missing.

## Step 4: Add the Operator Profile

Optional but recommended:

- create `local_pilot_runs/<operator_label>/operator_profile.md`
- use `docs/product/templates/Tender_Operator_Profile_Template.md`

Recommended fields:

- categories served
- excluded categories
- region preferences
- VAT mode
- target margin
- payment-delay tolerance
- security / guarantee tolerance
- required licenses or SRO
- supplier-search preferences

## Step 5: Add Supplier Search Notes

Optional but recommended:

- create or update `03_supplier_search/supplier_candidates.md`
- list candidate suppliers, notes, contacts, and RFQ status manually

The runner does not search the internet for suppliers.

## Step 6: Run the First Pass Without TKP

Use this run when documents are ready but supplier offers are not collected yet.

```bash
.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id <operator_label> \
  --tender-dir local_pilot_runs/<operator_label>/<tender_label> \
  --provider stub \
  --output-dir local_pilot_runs/<operator_label>/<tender_label>/05_system_output
```

Example:

```bash
.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider stub \
  --output-dir local_pilot_runs/tender_operator_001/tender_001/05_system_output
```

Expected console behavior:

- folder validation passes
- workspace is created
- 3 intake records are created
- analysis runs
- runner prints `No TKP files found`
- final status is `rfq_ready_collect_tkp`

## Step 7: Review First-Pass Outputs

Review these files in `05_system_output/`:

- `run_summary.json`
- `internal_operator_analysis.md`
- `requirements.json`
- `supplier_questions.json`
- `rfq_request_draft.md`
- `calibrated_contract_risk_memo.md`

And review these files in `06_partner_export/`:

- `operator_report.md`
- `export_summary.json`

What to check:

- `run_summary.json` contains `pilot_status=rfq_ready_collect_tkp`
- `supplier_questions.json` is usable for supplier outreach
- `rfq_request_draft.md` is usable as the starting RFQ text
- `export_summary.json` has no unexpected blocked sections

At this stage, these files should **not** exist:

- `tkp_comparison.json`
- `economics_summary.json`
- `bid_decision_recommendation.md`

## Step 8: Send RFQ Manually

Manual operator actions only:

1. review `rfq_request_draft.md`
2. tailor it for each supplier
3. send through email, messenger, portal, or another external channel
4. track responses in `03_supplier_search/`

No automated supplier outreach is generated by this script.

## Step 9: Save TKP Files

When supplier offers arrive, save them into:

- `04_tkp/supplier_001_tkp.*`
- `04_tkp/supplier_002_tkp.*`
- additional supplier files as needed

The current `stub` flow detects file presence and creates placeholder
comparison/economics outputs. Operator review is still required.

## Step 10: Re-run After TKP Collection

Run the same command again after `04_tkp/` contains supplier offers:

```bash
.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id <operator_label> \
  --tender-dir local_pilot_runs/<operator_label>/<tender_label> \
  --provider stub \
  --output-dir local_pilot_runs/<operator_label>/<tender_label>/05_system_output
```

Expected console behavior:

- runner detects TKP files
- TKP comparison is generated
- economics summary is generated
- preliminary bid recommendation is generated
- final status is `tkp_received_economics_ready`

## Step 11: Review Second-Pass Outputs

Additional files should now exist in `05_system_output/`:

- `tkp_comparison.json`
- `economics_summary.json`
- `bid_decision_recommendation.md`

Check specifically:

- `run_summary.json` contains `tkp_found=true`
- `run_summary.json` contains `pilot_status=tkp_received_economics_ready`
- `tkp_comparison.json` includes all supplier files from `04_tkp/`
- `bid_decision_recommendation.md` is treated as preliminary only

## Step 12: Human Review Before Delivery

Before sending anything externally:

1. read `06_partner_export/operator_report.md`
2. verify no internal-only notes leaked
3. verify no sensitive raw contract fragments leaked
4. verify commercial interpretation matches operator judgment
5. confirm the package is suitable for the partner

Use these docs together with the run:

- `Manual_Delivery_Checklist.md`
- `Partner_Report_Export_Policy.md`
- `Pilot_Operator_Error_Handling.md`

## Step 13: Deliver Manually

Actual delivery remains outside the repository:

- email
- secure portal
- messenger
- customer workspace

Only the reviewed partner-facing report should be sent:

- `06_partner_export/operator_report.md`

Do not send:

- `internal_operator_analysis.md`
- `requirements.json`
- `supplier_questions.json`
- `calibrated_contract_risk_memo.md`
- `tkp_comparison.json`
- `economics_summary.json`
- `run_summary.json`
- `export_summary.json`

## Step 14: Collect Feedback

After delivery:

- store notes in `07_feedback/`
- use `Partner_Feedback_Template.md` if needed
- record real partner feedback separately from the internal placeholder records

## Arguments

| Argument | Required | Default | Description |
|---|---|---|---|
| `--operator-id` | Yes | — | Operator identifier used in the internal workspace |
| `--tender-dir` | Yes | — | Tender folder containing `02_extracted_text/` |
| `--provider` | Yes | — | `stub` or `llm` |
| `--output-dir` | No | `<tender-dir>/05_system_output` | Directory for system output files |

## Provider Guidance

### `stub`

Use this by default for:

- environment smoke checks
- manual pilot rehearsals
- first operational runs

What it does:

- always works without external services
- generates deterministic placeholder analysis
- uses file presence in `04_tkp/` to decide whether to produce TKP/economics outputs

### `llm`

Use this only when the controlled LLM setup is intentionally enabled.

Minimum requirements:

- dependencies installed
- `AI_CORP_DATABASE_URL` configured
- `AI_CORP_OPENAI_API_KEY` configured
- compatible DB schema available for the controlled LLM path

If unavailable, the runner prints a warning and falls back to `stub`.

## Operational Notes

- `06_partner_export/` is always written under the tender folder even if `--output-dir` points elsewhere.
- Real raw tender files belong in ignored local folders only.
- Real TKP files belong in ignored local folders only.
- The script creates an internal workspace and intake records automatically.
- The script also writes partner export metadata automatically.
- The current script records internal placeholder feedback/outcome data for the run. Treat that as internal bookkeeping, not real partner feedback.
- The `delivered_manually` status is an internal marker only. It does **not** mean that the repository actually sent anything.
- Final bid submission remains fully manual.

## Troubleshooting

### Missing required text files

If the script fails at validation, confirm these exist:

- `02_extracted_text/notice.txt`
- `02_extracted_text/technical_spec.txt`
- `02_extracted_text/contract_draft.txt`

### No TKP outputs created

Check:

- `04_tkp/` exists
- supplier files are present inside `04_tkp/`
- you re-ran the command after saving those files

### `llm` falls back to `stub`

Check:

- `.env` or environment variables
- `AI_CORP_DATABASE_URL`
- `AI_CORP_OPENAI_API_KEY`
- DB accessibility from the current shell

### Export looks incomplete

Open:

- `06_partner_export/export_summary.json`

Review:

- `included_sections`
- `redacted_sections`
- `blocked_sections`

## Migration Note for Old PP1 Users

If you previously used `scripts/run_partner_tender_folder.py`:

1. the old PP1 flow still exists for backward compatibility
2. tender/operator customers should use `scripts/run_tender_operator_pilot.py`
3. the newer PP1R layout adds:
   `03_supplier_search/`, `04_tkp/`, `05_system_output/`, `06_partner_export/`, `07_feedback/`
4. the newer PP1R flow is RFQ-first and does not assume a fixed product catalog
