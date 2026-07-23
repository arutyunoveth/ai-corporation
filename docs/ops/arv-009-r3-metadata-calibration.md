# ARV-009 B2.2: R3 Metadata Storage Calibration

## Objective
Measure the per-case metadata storage footprint of R3 XML procurement documents on PostgreSQL and filesystem, then produce a capacity forecast for 5-year planning.

## Design

### Cohort
- **Source:** 18 R3 XML ZIP archives from EIS (real, publicly available).
- **Selection:** Uniform random sample from ~70 indexed R3 archives, stratified into tertiles by archive size.
- **Tertiles:** `lower` (6), `middle` (6), `upper` (6).
- **Scope:** Metadata only — no LLM, no embedding provider. Embeddings use `hashing` (dim=256).

### Infrastructure
- **PostgreSQL 17 + pgvector** in disposable Docker container (port 56432).
- **Filesystem:** `ARVECTUM_DATA_DIR` at `/tmp/arvectum-arv009-b22/data`.
- **Provider config:** `LLM=stub`, `embeddings=hashing`.

### Measurement Protocol
1. **Baseline (S0):** Record PG size + FS size after `alembic upgrade head` (empty DB).
2. **Per-case:** Ingest archives, build chunks, build embeddings. Snapshot PG + FS.
3. **Initial run:** Run analysis pipeline. Snapshot delta.
4. **Repeat runs:** Run pipeline again (2× for middle, 3× for upper tertile). Measure zero deltas as idempotency check.
5. **Backup (B2):** `pg_dump -Fc` after all 18 cases. Record compression ratio.

## Results

### Per-Case Storage (filesystem data delta)

| Group  | Min (B)  | P50 (B)  | Max (B)  | Mean (B)  |
|--------|----------|----------|----------|-----------|
| lower  | 218,539  | 274,950  | 296,021  | 258,765   |
| middle | 293,643  | 310,093  | 367,140  | 318,389   |
| upper  | 354,998  | 429,298  | 531,198  | 436,306   |

### Documents & Chunks
- 73 documents across 18 cases (mean 4.1 per case, 1–5 range).
- 15,293 chunks total (mean 850, range 485–1,179).
- Chunk count ≈ embedding rows (hashing).

### Compression
- **pg_dump compression ratio:** 1.49× (observed), 1.0× (forecast, conservative).
- **Metadata overhead (PG:FS growth):** 6.53×.

### Idempotency
Repeat runs on 6 cases (middle and upper tertile) showed zero measurable FS/PG delta — the pipeline produces identical output on re-run for the same input.

## Forecast (5-Year)

| Volume   | Cases/yr | Total Cases | Ingestion FS (mean) | Ingestion PG (mean) | Analysis Runs |
|----------|----------|-------------|---------------------|---------------------|---------------|
| Low      | 10,000   | 50,000      | 3.4 GB              | 150 MB              | 150,000       |
| High     | 100,000  | 500,000     | 34 GB               | 1.5 GB              | 1,500,000     |

All estimates use per-case FS mean of 338 KB and PG mean of 15 KB. Forecast uses conservative 1.0× compression ratio.

## Files

| Path | Description |
|------|-------------|
| `samples/capacity/public-r3-calibration.aggregate.json` | Public aggregate measurements |
| `samples/capacity/scenarios.public-r3-calibrated.json` | Forecast scenario |
| `scripts/capacity/calibration/calibrate_cohort.py` | Calibration harness |
| `scripts/capacity/calibration/peak_sampler.py` | Peak scenario sampler |
| `tests/capacity/test_aggregate_schema.py` | Schema validation tests |
| `tests/capacity/test_peak_sampler.py` | Peak sampler tests |
| `docs/ops/arv-009-r3-metadata-calibration.md` | This document |
