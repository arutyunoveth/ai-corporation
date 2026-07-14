# R1.B2 extraction report

## Scope and base

Base: `54c6c61`. Scope is EXTR-001 only; analysis, decisions and renderers were
not changed. Production DB and production ingest were not used.

## Root cause

`Обоснование НМЦК.docx` is extracted as tab-separated DOCX row text. The old
collector sent it only to the XLSX/goods parser, which requires a numeric first
cell and a quantity column. The real NMCK rows are service name, `Условная
единица`, and comparable unit prices; therefore every row was discarded.

## Implemented behaviour

`_extract_service_items_from_nmck_text` detects generic service-table rows by
unit and price semantics. It supports flattened DOCX/XLSX table text and
multi-line names, ignores headers/totals/notes, and produces service items with
deterministic evidence IDs derived from source document, table row and content.
It creates no fixed quantity, no per-row total and no inferred contract total.

For the source document it extracts 43 service rows. Each has an original
`Условная единица`, normalized unit, `quantity: null`,
`quantity_status: not_specified`, unit price, source row and evidence ID.

## Source-backed identity and price semantics

- Subject: vehicle diagnostics, maintenance and current repair services.
- Category: services; OKPD2 `45.20`.
- Procurement maximum: 500,000 RUB, retained as procurement-level value.
- The NMCK table is unit pricing; unit prices are not summed into NMCK or a
  contractual total.
- Draft contract is still missing; payment, penalties, acceptance and security
  remain unknown.

## Evidence and coverage

The parser records a source row number, original table fragment and stable
evidence ID for every service row. The golden source inventory still reports
the missing draft contract and the partially parsed NMCK table structure.

## Verification

- `tests/r1/test_service_table_extraction.py` and existing upload extraction
  regression tests: 20 passed.
- Secret scan: clean.
- `git diff --check`: clean.

The R1.A2 sharded exact-node verification remains the full-suite mechanism;
this B2 turn did not change its runner.

## Remaining defects and rollback

`ANL-001`, `ANL-002` and `RPT-001` remain open and were intentionally not
addressed. Revert the B2 commit to roll back the extraction behaviour.
R1.B3 should consume these source-backed service items in analysis/report.
