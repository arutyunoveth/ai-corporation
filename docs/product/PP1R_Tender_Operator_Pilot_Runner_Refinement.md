# PP1R — Tender Operator Pilot Runner Refinement

## Background

The first real customers are not manufacturers or suppliers with fixed product catalogs, known product lines, and known prices.

The first customers are tender/operator companies. They do not manufacture goods themselves, do not have a product catalog, and do not know supplier prices at the start. They search the market for suppliers, request TKP/commercial offers, compare offers, prepare bids, and manage fulfillment after winning.

This sprint refines PP1 to support the tender-operator workflow: RFQ-first, not product-catalog-first.

## What Changed

| Aspect | Old PP1 (partner/product-catalog) | New PP1R (tender-operator) |
|---|---|---|
| Profile | `partner_profile.md` (product catalog) | `operator_profile.md` (tender-operator constraints) |
| Folder structure | `03_operator_notes/`, `04_system_output/`, `05_partner_export/`, `06_feedback/` | `03_supplier_search/`, `04_tkp/`, `05_system_output/`, `06_partner_export/`, `07_feedback/` |
| Analysis focus | Product-line matching, known prices | Requirements extraction, RFQ preparation, contract risk calibration |
| Contract risk | Simple list of risks | Three-tier calibrated: market_standard_harsh_term, commercially_material_risk, deal_breaker_candidate |
| Output dir | `04_system_output/` | `05_system_output/` (shifted to accommodate new folders) |
| Milestone without TKP | Report ready | `rfq_ready` / `collect_tkp` |
| TKP mode | Not supported | Full TKP comparison, economics, bid decision when TKPs present |
| Command | `run_partner_tender_folder.py` | `run_tender_operator_pilot.py` (old PP1 kept for compatibility) |

## Scope Implemented

1. New script: `scripts/run_tender_operator_pilot.py`
2. New docs: PP1R sprint spec, calibrated contract risk method, RFQ workflow, operator profile template, folder template, runbook
3. Updated indexes: Operator_Runbook_MVP_v1.md, Product_Backlog.md, README.md
4. Tests: 30+ PP1R tests covering all scenarios
5. Backward compatibility: old PP1 script preserved with migration note

## Non-Goals Preserved

- No production UI
- No web button
- No automatic PDF/DOCX parsing
- No OCR
- No procurement platform integration
- No EDS/signature
- No supplier email automation
- No autonomous submission
- No external actions
- No product catalog matching as default behavior
