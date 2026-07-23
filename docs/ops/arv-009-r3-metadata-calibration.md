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
| Chunks per procurement | 832 | 985 | 1,021 | 1,179 |
| FS delta per procurement (B) | 307,009 | 390,495 | 512,435 | 531,198 |
| PG delta per procurement (B) | 8,192 | 8,192 | 24,576 | 122,880 |

### Per-group FS deltas (cumulative)
| Group | Total FS (B) | Cases |
|-------|-------------|-------|
| lower | 1,552,589 | 6 |
| middle | 3,462,923 | 12 |
| upper | 6,080,758 | 18 |

### Backup Measurements
| Metric | B1 (9 cases) | B2 (18 cases) |
|--------|-------------|---------------|
| `pg_dump` size | 2.8 MB | 4.5 MB |
| Unique live source | 3.2 MB | 6.1 MB |
| Archive-to-source ratio | 0.88 | 0.75 |
| Compression factor | 22.94 | 14.80 |

**Formulas:**
- `archive_to_source_ratio = total_backup_bytes / unique_live_source_bytes`
- `compression_factor = total_source_bytes / total_backup_bytes`
- Forecast uses `min(1.0, archive_to_source_ratio)` for conservative backup sizing.

### PostgreSQL Reconciliation
- `pg_database_size` delta includes schema overhead, WAL, autovacuum bloat.
- Relation-level deltas sum to less than `pg_database_size` delta.
- `pg_database_size` does not shrink after DELETEs.

### Temporary Peak Measurements
Per-tertile cumulative before/after FS deltas (each case ingestion completes faster than one 2-second sampling interval).

## Calibrated Parameters
- `documents_per_procurement` (p50=4, p75=4, p90=5)
- `extracted_text_bytes_per_procurement` (p50=113K, p75=139K, p90=156K)
- `chunks_per_procurement` (p50=832, p75=985, p90=1,021)
- `backup_compression_ratio` (0.7465, forecast uses 1.0×)
- `vector_dimension` (256)
- `embedding_rows_per_chunk` (1)
- `temporary_space_peak_factor` (19.83)

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
| `scripts/capacity/calibration/peak_sampler.py` | Peak filesystem sampler |
| `tests/capacity/test_aggregate_schema.py` | Schema and logic tests |
| `tests/capacity/test_peak_sampler.py` | Peak sampler tests |
| `docs/ops/arv-009-r3-metadata-calibration.md` | This document |

## Aggregate SHA-256
```
2ce8fb70524d8e8bfbb8c8849c93cd05307b606ab2df2256e05016d0aae9457d
```
