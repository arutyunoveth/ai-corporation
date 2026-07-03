# Tender Operator RFQ Workflow

## Overview

This document describes the RFQ-first workflow that tender operators use when preparing bids.

Tender operators do not have fixed product catalogs or known supplier prices. They search the market for each tender, request quotes, compare offers, and prepare bids based on collected data.

## Workflow Steps

### Step 1: Tender Documentation Analysis

1. Download tender documentation from the procurement portal.
2. Extract key requirements:
   - Subject of procurement
   - Technical specifications
   - Contract terms
   - Evaluation criteria
   - Required documents
   - Timeline and deadlines
3. Save extracted text to `02_extracted_text/`.

### Step 2: Requirements Extraction

1. Identify mandatory requirements (cannot be substituted).
2. Identify optional requirements (analogs may be acceptable).
3. Identify qualification requirements (licenses, SRO, experience).
4. Note any impossible or overly narrow requirements.

### Step 3: Supplier Search Preparation

1. Identify categories of goods/works/services needed.
2. Optionally import a local vendor-list into the existing Supplier Registry before ranking suppliers.
   - Supported formats: `.csv`, `.xlsx`
   - Supported columns: `legal_name`, `display_name`, `inn`, `website`, `email`, `phone`, `categories`, `brands`, `region`, `notes`
   - Russian aliases are supported for operational spreadsheets
   - Import remains a separate manual action and is never auto-triggered by the runner
3. Search internal supplier database or external sources.
   - Note: The system does not perform automatic internet search.
   - The operator must search manually.
4. Document potential supplier candidates in `03_supplier_search/`.
5. Supplier Search may combine:
   - canonical registry suppliers
   - vendor-list suppliers imported into the registry
   - manual operator notes from `03_supplier_search/supplier_candidates.md`
6. Relevance scoring should remain explainable.
   - Example signals: category, brand, region, contact completeness, vendor-list origin, tender-ready tags, extracted requirement/domain match
   - Human review remains required before any RFQ is sent externally

### Step 4: RFQ/TKP Request Preparation

1. Prepare supplier questions based on tender requirements.
2. Draft RFQ request for each supplier candidate.
3. Send manually via external channel.
   - Note: The system does not send automatic emails.
4. Save RFQ draft to `03_supplier_search/rfq_draft.md`.

### Step 5: TKP Collection

1. Receive TKP/commercial offers from suppliers via external channel.
2. Save each TKP to `04_tkp/` with a clear supplier label.
3. Track receipt status.
4. The system may normalize `.xlsx`, `.csv`, `.txt`, and `.md` TKP files into structured draft quotes.
5. PDF without safe extracted text remains manual-review territory in this sprint.

### Step 6: TKP Comparison

1. Compare offers side by side:
   - Price
   - Delivery time
   - Warranty
   - Payment terms
   - Certificates
2. Generate comparison table.
3. Use normalized quote drafts as input where extraction confidence is sufficient.
4. Keep human review for ambiguous line items, supplier matching, VAT assumptions, and unsupported formats.

### Step 7: Economics Calculation

1. Calculate total cost including:
   - Supplier prices
   - Delivery/logistics
   - Contract security cost
   - Financing cost (if prepayment required)
   - Margin
2. Determine final bid price.

### Step 8: Bid Decision

1. Review all factors:
   - Technical compliance
   - Commercial terms
   - Risk assessment
   - Margin
2. Make preliminary recommendation.
3. Prepare bid documents manually.
4. Submit via procurement platform.
   - Note: Submission remains fully manual.

## Vendor-List Import

Use the dedicated import script when the operator has a local supplier spreadsheet:

```bash
.venv/bin/python scripts/import_vendor_list.py \
  --operator-id tender_operator_001 \
  --file local_pilot_runs/tender_operator_001/vendor_list.xlsx \
  --source-label "vendor-list-2026-07"
```

Expected outputs:

- `local_pilot_runs/<operator_id>/vendor_imports/<timestamp>/vendor_import_summary.json`
- `local_pilot_runs/<operator_id>/vendor_imports/<timestamp>/vendor_import_report.md`

The import:

- creates or updates `SupplierProfile`
- adds `SupplierContact`, `SupplierExternalRef`, and `SupplierTag`
- deduplicates primarily by INN
- marks missing-INN rows for review instead of breaking the batch
- never sends email or performs any external action

## Milestone States

| State | Meaning |
|---|---|
| `tender_analyzed` | Tender documentation has been analyzed, requirements extracted |
| `rfq_ready` | RFQ/TKP request is ready to send to suppliers |
| `collect_tkp` | Awaiting TKP from suppliers |
| `tkp_received` | At least one TKP has been received |
| `economics_ready` | TKP comparison and economics calculated |
| `bid_decision_ready` | Preliminary bid decision recommendation ready |
| `bid_prepared` | Bid documents prepared (manual) |
| `submitted` | Bid submitted (manual — external to system) |
