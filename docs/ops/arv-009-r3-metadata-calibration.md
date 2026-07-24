# ARV-009 B2.2: R3 Metadata Storage Calibration

## Scope
R3/XML metadata ingestion calibration only. No attachments, no full document bodies, no AnalysisRun.

## Data Source
18 public R3 XML procurement archives from EIS, split into tertiles by archive size (lower=6, middle=6, upper=6). All archives are real publicly available XML metadata.

## Measurement Protocol

1. **Baseline:** Record `pg_database_size` and relation sizes after `alembic upgrade head` (empty schema).
2. **Per-case ingestion:** Copy ZIP archive, extract XML, create `ProcurementTender` + `ProcurementTenderDocument` records, build text chunks, compute hashing embeddings. Snapshot PG + FS after each case.
3. **Initial run:** Execute `TenderResearchPipeline.run_full()` (subprocess). Snapshot delta.
4. **Repeat runs:** Run pipeline again (2× for cases in REPEAT2 set, 3× for REPEAT3). Measure zero deltas as idempotency check.
5. **Backup B1:** After 9 cases, `pg_dump -Fc` of a database containing only the first 9 tenders.
6. **Backup B2:** After all 18 cases, `pg_dump -Fc`.
7. **Peak measurements:** Cumulative before/after filesystem deltas per tertile group.

## Providers
- **LLM:** `stub` (no generation cost)
- **Embeddings:** `hashing` (dim=256, no paid API)
- **Metadata fidelity:** `placeholder` (truncated field values)

## Results

### Documents & Chunks (18 cases)
| Metric | p50 | p75 | p90 | Max |
|--------|-----|-----|-----|-----|
| Documents per procurement | 4 | 4 | 5 | 5 |
| Extracted text (B) per procurement | 112,795 | 138,699 | 155,523 | 233,175 |
| Chunks per procurement | 832 | 985 | 1,021 | 1,266 |
| FS delta per procurement (B) | 1,895,971 | 2,214,572 | 2,483,196 | 2,657,169 |
| PG delta per procurement (B) | 1,611,231 | 1,943,378 | 2,179,107 | 2,367,200 |

### Character vs UTF-8 Byte Ratio
- Total extracted chars: 2,186,012
- Total UTF-8 bytes: 2,346,347
- Char→byte ratio: **1.073** (7.3% overhead for Russian XML data)

### Backup Measurements
| Metric | B1 (9 cases) | B2 (18 cases) |
|--------|-------------|---------------|
| `pg_dump` size | 2.7 MB | 4.4 MB |
| Unique live source | 19.1 MB | 35.8 MB |
| Archive-to-source ratio | 0.144 | 0.123 |
| Compression factor | 21.36 | 20.31 |

**Formulas:**
- `archive_to_source_ratio = total_backup_bytes / unique_live_source_bytes`
- `compression_factor = total_source_bytes / total_backup_bytes`
- Forecast uses `min(1.0, archive_to_source_ratio)` for conservative backup sizing.

### PostgreSQL Reconciliation
- `pg_database_size` delta includes schema overhead, WAL, autovacuum bloat.
- Relation-level deltas sum to less than `pg_database_size` delta.
- `pg_database_size` does not shrink after DELETEs.
- S0→S9: PG +16.7 MB, S9→S18: PG +14.2 MB.
- `pg_database_size` grows faster than relation logical bytes due to block-level allocation.

### Temporary Peak Measurements
Continuous peak sampling via `peak_sampler.py` at ≥2s intervals. Peak delta reflects the maximum observed logical/allocated bytes during ingestion. SIGINT/SIGTERM captures a final sample before exit. The `--oneshot` flag has been removed; all runs now capture a final signal-triggered sample.

## Calibrated Parameters
- `documents_per_procurement` (p50=4, p75=4, p90=5)
- `extracted_text_bytes_per_procurement` (p50=112,795, p75=138,699, p90=155,523)
- `chunks_per_procurement` (p50=832, p75=985, p90=1,021)
- `backup_compression_ratio` (0.123, forecast uses 1.0×)
- `vector_dimension` (256)
- `embedding_rows_per_chunk` (1)
- `temporary_space_peak_factor` (165.0)

## Uncalibrated Parameters (Kept as Original Assumptions)
- `procurements_per_month`
- `analysis_runs_per_procurement`
- `raw_document_bytes_per_procurement`
- `database_non_vector_bytes_per_procurement`
- `database_non_vector_bytes_per_run`
- `report_artifact_bytes_per_run`
- `other_artifact_bytes_per_run`
- Full backup retention count
- Operational margin

Reason: these parameters require production deployment data, full-document calibration, or AnalysisRun integration that is not available in this R3/XML metadata-only measurement.

## AnalysisRun Status
**Unavailable.** The R8 `create_analysis_run()` path exists in `history_service.py` but is not wired to any pipeline or CLI. No `TenderAnalysisRun` rows were created during measurements (`analysis_run_count=0`). All "analysis run" measurements use `TenderResearchPipeline.run_full()` subprocess, which produces PG/FS deltas without creating formal AnalysisRun records.

## Forecast Command
```bash
python scripts/capacity/arv_capacity.py forecast \
  --snapshot <snapshot> \
  --scenario samples/capacity/scenarios.public-r3-calibrated.json \
  --years 1,3,5 \
  --output-dir /tmp/arv009-b2-forecast
```

## Limitations
- R3/XML metadata only — no attachments, no full document bodies.
- Embedding provider: hashing (dim=256). Not a production embedding model.
- LLM: stub. No generation cost measured.
- Metadata fidelity: placeholder (truncated field values).
- AnalysisRun not available — pipeline subprocess used.
- This is a lower-bound estimate for R3 metadata storage.
- **No customer data was used.**
- **This is an R3/XML metadata-ingestion calibration.**
- **This is not a production capacity guarantee.**
- **No final VPS provider or server was selected.**

## Files
| Path | Description |
|------|-------------|
| `samples/capacity/public-r3-calibration.aggregate.json` | Aggregate measurements (public) |
| `samples/capacity/scenarios.public-r3-calibrated.json` | Calibrated forecast scenario |
| `scripts/capacity/calibration/calibrate_cohort.py` | Deterministic calibration harness |
| `scripts/capacity/calibration/peak_sampler.py` | Peak filesystem sampler (SIGINT/TERM captures final sample; no --oneshot) |
| `tests/capacity/test_aggregate_schema.py` | Schema and logic tests |
| `tests/capacity/test_peak_sampler.py` | Peak sampler tests |
| `docs/ops/arv-009-r3-metadata-calibration.md` | This document |

## Aggregate SHA-256
```
425e53706e44721c9bc3dce1b055f25ba3511ca669fdf00113c2774ef03500e3
```
