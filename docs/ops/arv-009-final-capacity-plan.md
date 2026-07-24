# ARV-009 Final Capacity Plan

## 1. Purpose

This document presents the final disk capacity plan for the Arvectum AI Corporation platform, based on the R3/XML metadata ingestion calibration (ARV-009B2) and the baseline snapshot of `main` at commit `efe1821`. It provides a storage envelope for three deployment profiles across three planning horizons.

## 2. Canonical Main Commit

```
efe182182a3a6a6299c8a384f3257fc0c9d891c6
```

## 3. Inputs and SHA-256

| Input | File | SHA-256 |
|-------|------|---------|
| Calibration aggregate | `public-r3-calibration.aggregate.json` | `8b1a1fd6d0ed994da8b8af04930951d58ba7a1d7b6ef88d256f08e143b527b58` |
| Calibrated scenario | `scenarios.public-r3-calibrated.json` | (embedded in plan JSON) |
| Baseline snapshot | `arv-009-final-baseline.snapshot.json` | (embedded in plan JSON) |

## 4. What Was Measured

- Documents per procurement (p50=4, p75=4, p90=5)
- Extracted text UTF-8 bytes per procurement (p50=121,916, p75=144,233, p90=162,378)
- Chunks per procurement (p50=832, p75=985, p90=1,021)
- Embedding rows per chunk: 1
- Local hashing vector dimension: 256
- Vector bytes per component: 4
- Backup compression ratio: B1=0.0572, B2=0.0934, forecast=0.0934
- Database baseline: 22.7 MB (empty schema after all migrations)
- Filesystem baseline: 0 bytes (empty production-like roots)

## 5. What Remains Assumed

- Procurements per month
- Raw document bytes per procurement
- Analysis runs per procurement
- Database non-vector bytes per procurement/run
- Report/other artifact sizes
- Full backups retained count
- Temporary space peak factor
- Operational margin
- Free space reserve percent

## 6. Baseline Snapshot

The baseline snapshot was taken against an empty PostgreSQL 17 database with pgvector 0.8.5, all 96 migrations applied, and empty production-like filesystem roots (data, artifacts, eis-archives, company-agent-runs, backups). Database size after migrations: 22,730,419 bytes (21.7 MB).

## 7. Forecast Methodology

The forecast uses the built-in `arv_capacity.py forecast` command with the calibrated scenario and baseline snapshot. Growth is linear over time based on per-procurement and per-run parameters. Backup storage accounts for retained full backups at the observed compression ratio. Temporary storage applies the peak factor to primary+backup total.

## 8. Matrix: 3 Profiles × 3 Horizons

| Profile | Years | Procurements | Analysis Runs | Primary (GiB) | Backups (GiB) | Temp (GiB) | Margin (GiB) | Reserve (GiB) | Total (GiB) | Floor (GiB) |
|---------|-------|-------------|---------------|--------------|--------------|-----------|-------------|--------------|------------|------------|
| pilot | 1 | 60 | 180 | 49.3 | 32.2 | 73.9 | 10.0 | 44.5 | 210.0 | 210 |
| pilot | 3 | 180 | 540 | 147.8 | 96.7 | 221.8 | 10.0 | 123.7 | 600.0 | 600 |
| pilot | 5 | 300 | 900 | 246.4 | 161.1 | 369.6 | 10.0 | 202.9 | 990.0 | 990 |
| commercial_mvp | 1 | 600 | 3000 | 1215.9 | 1589.9 | 1823.9 | 20.0 | 1550.5 | 6200.0 | 6200 |
| commercial_mvp | 3 | 1800 | 9000 | 3647.7 | 4769.7 | 5471.5 | 20.0 | 4641.2 | 18550.0 | 18550 |
| commercial_mvp | 5 | 3000 | 15000 | 6079.4 | 7949.4 | 9119.1 | 20.0 | 7732.0 | 30900.0 | 30900 |
| scaling | 1 | 6000 | 60000 | 53444.3 | 149750.9 | 69477.6 | 50.0 | 54544.5 | 327270.0 | 327270 |
| scaling | 3 | 18000 | 180000 | 160332.8 | 449252.4 | 208432.6 | 50.0 | 163613.6 | 981690.0 | 981690 |
| scaling | 5 | 30000 | 300000 | 267221.3 | 748754.0 | 347387.7 | 50.0 | 272682.6 | 1636100.0 | 1636100 |

## 9. Controlled Pilot Configuration

**Reference horizon:** 1 year (also shown at 3 and 5 years)

| Component | 1 Year (GiB) | 3 Years (GiB) | 5 Years (GiB) |
|-----------|-------------|--------------|--------------|
| PostgreSQL/database | 9.4 | 28.3 | 47.1 |
| Vectors | 0.05 | 0.14 | 0.24 |
| Raw documents | 29.3 | 87.9 | 146.5 |
| Extracted text | <0.1 | <0.1 | <0.1 |
| Report/run artifacts | 10.5 | 31.6 | 52.7 |
| Retained backups | 32.2 | 96.7 | 161.1 |
| Temporary space | 73.9 | 221.8 | 369.6 |
| OS/runtime margin | 10.0 | 10.0 | 10.0 |
| Free-space reserve | 44.5 | 123.7 | 202.9 |
| **Total** | **210.0** | **600.0** | **990.0** |
| **Provisioned floor** | **210 GiB** | **600 GiB** | **990 GiB** |

**Five largest disk drivers:** temporary_storage_bytes > retained_backups_bytes > raw_documents_bytes > primary_storage_bytes > free_space_reserve_bytes

## 10. Commercial MVP Configuration

**Reference horizon:** 3 years (also shown at 1 and 5 years)

| Component | 1 Year (GiB) | 3 Years (GiB) | 5 Years (GiB) |
|-----------|-------------|--------------|--------------|
| PostgreSQL/database | 264.3 | 792.7 | 1321.2 |
| Vectors | 0.56 | 1.69 | 2.82 |
| Raw documents | 600.0 | 1800.0 | 3000.0 |
| Extracted text | 0.08 | 0.24 | 0.40 |
| Report/run artifacts | 351.6 | 1054.7 | 1757.8 |
| Retained backups | 1589.9 | 4769.7 | 7949.4 |
| Temporary space | 1823.9 | 5471.5 | 9119.1 |
| OS/runtime margin | 20.0 | 20.0 | 20.0 |
| Free-space reserve | 1550.5 | 4641.2 | 7732.0 |
| **Total** | **6200.0** | **18550.0** | **30900.0** |
| **Provisioned floor** | **6200 GiB** | **18550 GiB** | **30900 GiB** |

**Five largest disk drivers:** temporary_storage_bytes > retained_backups_bytes > primary_storage_bytes > free_space_reserve_bytes > raw_documents_bytes

## 11. Scaling Configuration

**Reference horizon:** 5 years (also shown at 1 and 3 years)

| Component | 1 Year (GiB) | 3 Years (GiB) | 5 Years (GiB) |
|-----------|-------------|--------------|--------------|
| PostgreSQL/database | 8794.9 | 26384.7 | 43974.5 |
| Vectors | 5.84 | 17.53 | 29.21 |
| Raw documents | 30000.0 | 90000.0 | 150000.0 |
| Extracted text | 0.91 | 2.72 | 4.54 |
| Report/run artifacts | 14648.4 | 43945.3 | 73242.2 |
| Retained backups | 149750.9 | 449252.4 | 748754.0 |
| Temporary space | 69477.6 | 208432.6 | 347387.7 |
| OS/runtime margin | 50.0 | 50.0 | 50.0 |
| Free-space reserve | 54544.5 | 163613.6 | 272682.6 |
| **Total** | **327270.0** | **981690.0** | **1636100.0** |
| **Provisioned floor** | **327270 GiB** | **981690 GiB** | **1636100 GiB** |

**Five largest disk drivers:** retained_backups_bytes > temporary_storage_bytes > primary_storage_bytes > free_space_reserve_bytes > raw_documents_bytes

## 12. Component Breakdown

At the commercial MVP 3-year reference point, the storage requirement breaks down as:

- **Primary storage:** 3,647.7 GiB (19.7%) — database + files
- **Backups:** 4,769.7 GiB (25.7%) — retained full backups at 0.0934 ratio
- **Temporary:** 5,471.5 GiB (29.5%) — peak processing workspace
- **Margin:** 20.0 GiB (0.1%) — OS/runtime overhead
- **Reserve:** 4,641.2 GiB (25.0%) — free-space reserve

## 13. Single-Volume Layout

All persistent storage, local backups, temporary space, operational margin, and reserve on a single volume. For the commercial MVP 3-year horizon: **18,550 GiB**.

## 14. Split-Volume Layout

| Volume | Contents | Estimated Size (MVP 3y) |
|--------|----------|------------------------|
| Database volume | PostgreSQL data, vectors | ~800 GiB |
| Documents/artifacts volume | Raw docs, extracted text, reports, other artifacts | ~2,855 GiB |
| Temporary volume | Ingestion/analysis temp workspace | ~5,472 GiB |
| Backup storage | Retained full backups | ~4,770 GiB |
| OS/runtime volume | OS, Docker images, logs, services | ~20 GiB + reserve |

Off-host backup storage is operationally preferable, but ARV-009 keeps retained backups in the total requirement until ARV-011 chooses the deployment topology.

## 15. Sensitivity Analysis

The following assumption parameters have the largest impact on total storage:

1. **procurements_per_month** — directly scales all volume-related components
2. **raw_document_bytes_per_procurement** — dominates filesystem primary storage
3. **full_backups_retained** — proportionally scales backup storage
4. **other_artifact_bytes_per_run** — significant at scale due to high run counts
5. **report_artifact_bytes_per_run** — moderate impact across all profiles

Each parameter was tested at 0.5×, 1.0×, and 2.0× of its assumed value. Full results are in the plan JSON.

## 16. Five Largest Disk Drivers

1. **temporary_storage_bytes** — temporary peak processing (largest single component across all profiles except scaling where backups dominate)
2. **retained_backups_bytes** — retained full backup archives
3. **primary_storage_bytes** — database + persistent files
4. **free_space_reserve_bytes** — built-in 20-25% headroom
5. **raw_documents_bytes** — source document storage

## 17. Metadata-Only Lower Bound

If only metadata components are considered (no attachments, no production embeddings, no AnalysisRun artifacts, no LLM outputs):

- 1-year pilot: <10 GiB
- 3-year commercial MVP: <30 GiB
- 5-year scaling: <100 GiB

This lower-bound view is not a disk recommendation. It illustrates metadata-only storage requirements without full-document or production workload components.

## 18. Attachment Limitation

All projections exclude procurement attachments (PDF, DOCX, images). The R3/XML calibration measured metadata only. Full-document storage will be significantly larger.

## 19. AnalysisRun Limitation

AnalysisRun artifacts are not available in R3. The pipeline subprocess was used for measurements. All AnalysisRun-related storage parameters remain assumptions.

## 20. Production Embedding Limitation

Embedding measurements used hashing (dim=256). A production embedding model will use higher dimensions (768–3072) and may generate multiple vectors per chunk, significantly increasing vector storage.

## 21. Temporary-Space Limitation

Temporary peak measurements are unavailable (no continuous sampling in R3 metadata ingestion). Template default factors are retained: pilot=1.5, commercial_mvp=1.5, scaling=1.3.

## 22. Backup Topology Limitation

All retained backups are calculated as local on-disk storage. Off-host or remote backup storage is not assumed. The backup ratio (0.0934) is based on metadata-only measurement; full-document backups will have different characteristics.

## 23. ARV-010 Gate

| Item | Status |
|------|--------|
| Basic contour | Ready |
| Structured runtime metrics | Remaining |
| Error monitoring | Remaining |
| Jobs/queue monitoring | Remaining |
| Regular restore drill | Remaining |
| CPU/RAM/load evidence | Remaining |

ARV-009 completion does not unblock VPS purchase by itself. ARV-011 still requires ARV-010 completion and CPU/RAM evidence.

## 24. ARV-011 Handoff

| Parameter | Status |
|-----------|--------|
| Storage envelope | Ready for provider comparison |
| CPU requirements | Not measured |
| RAM requirements | Not measured |
| Runtime metrics | Blocked by ARV-010 |
| Provider | Not selected |
| Server | Not purchased |

## 25. Reproduction Commands

```bash
# Set up environment
export AI_CORP_DATABASE_URL=postgresql://user:pass@host:port/dbname
export PYTHONPATH=.

# Take baseline snapshot
python scripts/capacity/arv_capacity.py snapshot \
  --output-dir /tmp/baseline \
  --root "data=/path/to/data"

# Run forecast
python scripts/capacity/arv_capacity.py forecast \
  --snapshot samples/capacity/arv-009-final-baseline.snapshot.json \
  --scenario samples/capacity/scenarios.public-r3-calibrated.json \
  --years 1,3,5 \
  --output-dir /tmp/forecast

# Build final plan
python scripts/capacity/planning/build_final_plan.py \
  --snapshot samples/capacity/arv-009-final-baseline.snapshot.json \
  --scenario samples/capacity/scenarios.public-r3-calibrated.json \
  --aggregate samples/capacity/public-r3-calibration.aggregate.json \
  --forecast-json /tmp/forecast/capacity_forecast.json \
  --json-output samples/capacity/arv-009-final-capacity-plan.json \
  --csv-output samples/capacity/arv-009-final-capacity-plan.csv \
  --markdown-output /tmp/arv009-b3-plan.md
```

## 26. Privacy Controls

- No customer data was used
- No private procurement corpus was read during ARV-009B3
- All sample files contain only public R3/XML metadata
- The baseline snapshot is sanitized (no DSN, hostname, absolute paths)
- The plan contains no procurement numbers, case IDs, or private manifest paths

## 27. Final Decision Statement

- No VPS provider was selected
- No server was purchased
- CPU and RAM requirements were not determined by ARV-009
- This is a planning envelope, not a production capacity guarantee
- Full-document calibration remains outstanding
- ARV-009 provides the disk envelope; ARV-011 combines storage + CPU/RAM + provider constraints
- Do not purchase VPS before ARV-011
