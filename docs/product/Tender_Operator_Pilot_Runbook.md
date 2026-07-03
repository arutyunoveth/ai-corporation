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

## Step 5A: Import a Vendor-List Into Supplier Registry

Use this step when the operator already has a local supplier spreadsheet and wants
the existing Supplier Registry and Supplier Search modules to reuse it.

Supported formats:

- `.csv`
- `.xlsx`

Supported columns:

- `legal_name`
- `display_name`
- `inn`
- `website`
- `email`
- `phone`
- `categories`
- `brands`
- `region`
- `notes`

Russian aliases are also supported, including `Юрлицо`, `Наименование`,
`Название`, `ИНН`, `Сайт`, `Почта`, `Телефон`, `Категории`, `Бренды`,
`Регион`, and `Примечание`.

Example spreadsheet shape:

```text
| Наименование        | ИНН        | Сайт              | Почта            | Категории          | Бренды | Регион |
|---------------------|------------|-------------------|------------------|--------------------|--------|--------|
| ООО Электро Поставка | 7701234567 | electro.example.ru | sales@example.ru | Electro;Automation | IEK    | Moscow |
```

Run the import manually:

```bash
.venv/bin/python scripts/import_vendor_list.py \
  --operator-id tender_operator_001 \
  --file local_pilot_runs/tender_operator_001/vendor_list.xlsx \
  --source-label "vendor-list-2026-07"
```

Expected outputs:

- `local_pilot_runs/<operator_label>/vendor_imports/<timestamp>/vendor_import_summary.json`
- `local_pilot_runs/<operator_label>/vendor_imports/<timestamp>/vendor_import_report.md`

What the import does:

- creates or updates canonical `SupplierProfile` records
- adds `SupplierContact`, `SupplierExternalRef`, and `SupplierTag`
- deduplicates primarily by INN
- marks missing-INN rows for review instead of aborting the batch
- flags possible duplicates for human review instead of auto-merging

What it does not do:

- does not send RFQ email
- does not submit anything to procurement platforms
- does not sign anything

The tender runner does not auto-import vendor-lists. Keep import as a deliberate,
separate operator action.

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
- `run_summary.json` contains `requested_provider` and `resolved_provider`
- `run_summary.json` contains `supplier_sourcing`
- `supplier_questions.json` is usable for supplier outreach
- `rfq_request_draft.md` is usable as the starting RFQ text
- `export_summary.json` has no unexpected blocked sections

If supplier registry data is available, also check:

- `supplier_sourcing.registry_supplier_count`
- `supplier_sourcing.vendor_list_supplier_count`
- `supplier_sourcing.top_suppliers[*].inclusion_reason`

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
| `--provider` | Yes | — | `stub`, `llm`, `openai_compatible`, `gigachat`, `yandex`, `alice`, or `cloudru` |
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

### `llm` (legacy entrypoint)

Use this when you want the runner to read `AI_CORP_LLM_PROVIDER` from the environment.

Minimum requirements:

- dependencies installed
- `AI_CORP_DATABASE_URL` configured
- `AI_CORP_LLM_PROVIDER` configured to the intended backend
- compatible DB schema available for the controlled LLM path

If unavailable, the runner prints a warning and falls back to `stub`.

### Explicit cloud provider flags

Use these when you want the CLI invocation to force the backend regardless of `AI_CORP_LLM_PROVIDER`:

- `openai_compatible`
- `gigachat`
- `yandex`
- `alice`
- `cloudru`

The run summary records both:

- `requested_provider`
- `resolved_provider`

`resolved_provider` becomes `stub` if the cloud path fails and the runner falls back safely.

## Launch Examples

### Stub

```bash
.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider stub
```

### Legacy `llm` entrypoint via environment

```bash
export AI_CORP_LLM_PROVIDER=gigachat
export AI_CORP_LLM_MODEL=GigaChat

.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider llm
```

### Force OpenAI-compatible

```bash
export AI_CORP_LLM_MODEL=gpt-4.1-mini

.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider openai_compatible
```

### Force GigaChat

```bash
export AI_CORP_LLM_MODEL=GigaChat

.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider gigachat
```

### Force Yandex AI Studio

```bash
export AI_CORP_LLM_MODEL=<yandex-model-id>

.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider yandex
```

### Force Alice AI

```bash
export AI_CORP_LLM_MODEL=<alice-model-id>

.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider alice
```

### Force Cloud.ru

```bash
export AI_CORP_LLM_MODEL=<cloudru-model-id>

.venv/bin/python scripts/run_tender_operator_pilot.py \
  --operator-id tender_operator_001 \
  --tender-dir local_pilot_runs/tender_operator_001/tender_001 \
  --provider cloudru
```

## Cloud LLM Data Handling

Default posture for cloud-provider runs:

- `AI_CORP_LLM_ALLOW_RAW_PARTNER_DATA=false`
- `AI_CORP_LLM_STORE_RAW_RESPONSE=false`
- human review is required for all LLM-generated artifacts
- external actions remain manual only

What this means:

- provider-bound context is sanitized before sending when raw partner data is not explicitly allowed
- runtime traces record `redaction_applied`, `input_chars_before`, and `input_chars_after`
- raw LLM responses are not persisted by default
- deterministic economics stay in Python and are not delegated to the LLM

Recommended local setup:

```bash
cp .env.example .env.local
```

Example `.env.local` shape without real secrets:

```bash
AI_CORP_DATABASE_URL=sqlite:///./ai_corporation.db
AI_CORP_LLM_PROVIDER=stub
AI_CORP_LLM_MODEL=
AI_CORP_LLM_ALLOW_RAW_PARTNER_DATA=false
AI_CORP_LLM_STORE_RAW_RESPONSE=false

AI_CORP_OPENAI_API_KEY=
AI_CORP_OPENAI_BASE_URL=https://api.openai.com/v1

AI_CORP_GIGACHAT_AUTH_KEY=
AI_CORP_GIGACHAT_SCOPE=GIGACHAT_API_PERS
AI_CORP_GIGACHAT_OAUTH_URL=https://ngw.devices.sberbank.ru:9443/api/v2/oauth
AI_CORP_GIGACHAT_BASE_URL=https://gigachat.devices.sberbank.ru/api/v1

AI_CORP_YANDEX_API_KEY=
AI_CORP_YANDEX_IAM_TOKEN=
AI_CORP_YANDEX_BASE_URL=https://ai.api.cloud.yandex.net/v1

AI_CORP_CLOUDRU_API_KEY=
AI_CORP_CLOUDRU_BASE_URL=https://foundation-models.api.cloud.ru/v1
```

## Operational Notes

- Imported vendor-lists stay local-only and must not be committed.
- `06_partner_export/` is always written under the tender folder even if `--output-dir` points elsewhere.
- Real raw tender files belong in ignored local folders only.
- Real TKP files belong in ignored local folders only.
- The script creates an internal workspace and intake records automatically.
- The script also writes partner export metadata automatically.
- The current script records internal placeholder feedback/outcome data for the run. Treat that as internal bookkeeping, not real partner feedback.
- The `delivered_manually` status is an internal marker only. It does **not** mean that the repository actually sent anything.
- Final bid submission remains fully manual.
- Imported vendor-list suppliers can influence shortlist ordering, but RFQ sending remains manual.

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
- provider-specific credentials for the resolved backend
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
