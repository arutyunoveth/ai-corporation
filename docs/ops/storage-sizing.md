# ARV-009: Storage Capacity Toolkit

## 1. Purpose

ARV-009 defines a read-only toolkit (`arv_capacity.py`) that measures
current storage usage across PostgreSQL/pgvector, filesystem artifact
stores, and existing backups, then produces a multi-year disk capacity
forecast.

The toolkit is designed for the R7 baseline and will automatically
cover new relations after the R8 merge (see section 11).

## 2. Storage Map (R7)

```
PostgreSQL / pgvector
  ├── tables (heap / main fork)
  ├── TOAST
  ├── indexes (btree, pgvector ivfflat/hnsw)
  └── vector columns (embedding)
Filesystem
  ├── data/                        — extracted texts, structured data
  ├── artifacts/                   — reports, generated documents
  ├── eis-archives/                — EIS SOAP archives, XML
  ├── company_agent_runs/          — per-company agent run artifacts
  └── tmpfs /tmp                   — ephemeral processing space
Backup
  ├── database.dump                — pg_dump
  ├── artifacts.tar.gz             — compressed file artifacts
  ├── manifest.json                — backup metadata
  └── SHA256SUMS                   — checksums
```

## 3. What the toolkit measures

- **PostgreSQL**: `pg_database_size`, `pg_total_relation_size`,
  `pg_indexes_size`, `pg_table_size`, `pg_relation_size` (main fork),
  TOAST via `reltoastrelid`, `reltuples`, `pg_stat_user_tables`,
  `pg_extension` for pgvector version, `pg_attribute` for vector column
  detection with dimension and kind (vector/halfvec/sparsevec), index
  access methods with `is_vector_index` flag.
- **Filesystem**: logical bytes, allocated blocks, file/directory counts,
  bytes by extension, bytes by first-level directory, top-20 largest files,
  temp files (*.tmp, *.partial, *.part), symlink count, storage identity
  (device+inode hash) for deduplication.
- **Backup**: file existence and size of database.dump, artifacts.tar.gz,
  manifest.json, SHA256SUMS; safe metadata read from manifest.json;
  compression ratio against multiple live source roots.

## 4. What the toolkit does NOT do

- Does not run DDL, DML, VACUUM, ANALYZE, or CREATE EXTENSION.
- Does not read document contents, chunk texts, embedding values,
  customer names, procurement numbers, or JSON field values.
- Does not follow symlinks during filesystem walk.
- Does not traverse root symlinks.
- Does not extract archives or run pg_restore.
- Does not compute SHA-256 of file contents.
- Does not commit generated output.
- Does not open or merge pull requests.

## 5. Read-only guarantees

- PostgreSQL: connection-level `read_only = True` via psycopg,
  verified with `SHOW default_transaction_read_only` and
  `SHOW transaction_read_only`. `SET statement_timeout = '30s'`.
- `read_only_verified` field in output; database is marked available
  only if read-only is confirmed.
- Each metric query is isolated; a single query failure does not
  discard already collected data. `ROLLBACK` clears aborted transaction
  state after each error.
- All filesystem operations use `os.stat` / `os.lstat` with
  `followlinks=False`; no file contents are read.
- Backup analysis reads only manifest.json metadata; archives remain
  untouched.
- No DSN, hostname, username, database name, password, or raw exception
  text is included in any output.

## 6. Commands

### snapshot

```shell
python scripts/capacity/arv_capacity.py snapshot \
  --database-url-env AI_CORP_DATABASE_URL \
  --root pilot-data=/path/to/data \
  --root pilot-artifacts=/path/to/artifacts \
  --root pilot-eis=/path/to/eis-archives \
  --root company-agent-runs=/path/to/company_agent_runs \
  --backup-dir /path/to/existing/backup \
  --backup-source-root pilot-data \
  --backup-source-root pilot-artifacts \
  --backup-source-root pilot-eis \
  --output-dir /tmp/arvectum-capacity/snapshot
```

Options:

| Flag | Purpose |
|---|---|
| `--database-url-env` | Env variable name holding DSN (default: `AI_CORP_DATABASE_URL`) |
| `--root name=path` | Named filesystem root (repeatable) |
| `--backup-dir` | Path to existing backup directory (optional) |
| `--backup-source-root` | Root name(s) for backup archive source bytes (repeatable) |
| `--output-dir` | Output directory (default: `~/arvectum-capacity/snapshot`) |
| `--no-db` | Skip database collection |
| `--no-files` | Skip filesystem collection |
| `--include-relative-paths` | Include relative paths in top-files listing |

Outputs: `capacity_snapshot.json`, `capacity_relations.csv`,
`capacity_files.csv`, `capacity_report.md`.

### forecast

```shell
python scripts/capacity/arv_capacity.py forecast \
  --snapshot /tmp/arvectum-capacity/snapshot/capacity_snapshot.json \
  --scenario samples/capacity/scenarios.example.json \
  --years 1,3,5 \
  --output-dir /tmp/arvectum-capacity/forecast
```

Options:

| Flag | Purpose |
|---|---|
| `--snapshot` | Path to previous snapshot JSON (optional, adds measured baseline) |
| `--scenario` | Scenario profile JSON (required) |
| `--years` | Comma-separated year horizons (default: `1,3,5`) |
| `--output-dir` | Output directory (default: `~/arvectum-capacity/forecast`) |

Outputs: `capacity_forecast.json`, `capacity_forecast.csv`,
`capacity_forecast.md`.

## 7. Forecast formula

```
baseline_database       = measured database_size_bytes (or 0)
baseline_filesystem     = sum(measured unique roots)
incremental_database    = forecast new procurements/runs/vectors
incremental_filesystem  = forecast new documents/texts/artifacts
projected_database      = baseline_database + incremental_database
projected_filesystem    = baseline_filesystem + incremental_filesystem

primary_storage         = projected_database + projected_filesystem
backup_storage          = estimated_full_backup_size * full_backups_retained
temporary_storage       = primary_storage * temporary_space_peak_factor
raw_required            = primary_storage + backup_storage + temporary_storage
                          + operational_margin_bytes
recommended_disk        = raw_required / (1 - free_space_reserve_percent / 100)
```

`recommended_disk` is rounded up to the nearest 10 GiB.

Each projection shows `baseline`, `incremental`, and `projected_total`
separately with their source annotations.

## 8. Measured / Derived / Assumed / Unavailable

| Source | Meaning |
|---|---|
| `measured` | Value read from live system (database size, file bytes) |
| `derived`  | Value computed from measured data or assumptions (sums, projections) |
| `assumed`  | Value from scenario profile (not actual production data) |
| `unavailable` | Baseline not provided (treated as zero) |

The `samples/capacity/scenarios.example.json` file contains only
`assumed` values. They must be replaced with measured or derived values
before making procurement decisions.

## 9. pgvector estimation limitations

- Vector column detection reads `pg_attribute` + `pg_type` to find
  columns of type `vector`, `halfvec`, or `sparsevec`.
- The declared dimension is read from `format_type()`.
- Actual row count uses `reltuples` (estimated by autovacuum), not
  `COUNT(*)`.
- Embedding storage calculation is:
  - `vector`: `rows × dimension × 4 bytes` (float32)
  - `halfvec`: `rows × dimension × 2 bytes` (float16)
  - `sparsevec`: no estimate (warning issued)
- Actual storage may differ due to index overhead, TOAST, and pgvector
  index structures (IVFFlat / HNSW).
- Vector indexes are detected by access method (`hnsw`, `ivfflat`) and
  flagged with `is_vector_index: true`.

## 10. Filesystem deduplication

R7 mounts one Docker volume at multiple paths (`/app/artifacts`,
`/app/company_agent_runs`). The toolkit detects duplicate storage by
computing `storage_identity_id` from `(st_dev, st_ino)`.

- First occurrence is `counted_in_totals: true`.
- Subsequent occurrences show `alias_of: <first_root_name>` and
  `counted_in_totals: false`.
- Backup compression ratio and baseline sums use only unique roots.

## 11. Why not to choose VPS by empty-DB size

A fresh PostgreSQL installation with empty vector tables reports near-zero
database size. The primary storage cost driver is the accumulated
procurement documents, extracted text, embeddings, and analysis runs
over months and years. Always run the forecast with realistic
assumptions matching the expected procurement volume.

## 12. Re-running after R8 merge

1. Rebase this branch on the new `origin/main` after R8 merges.
2. Run `snapshot` again with the same (or updated) root paths.
3. The PostgreSQL collector reads `pg_catalog` dynamically — new
   tables, columns, and vector fields from R8 appear automatically.
4. Update `samples/capacity/scenarios.example.json` assumptions if
   R8 changes storage patterns (e.g., new embedding dimensions,
   additional artifact types).

## 13. Output schema history

| Version | Changes |
|---|---|
| `1.0` | Initial toolkit |
| `1.1` | Read-only verification, baseline-aware forecast, deduplicated roots, accurate PostgreSQL breakdown, per-metric status, path sanitization |

Generated output must NOT be committed.

## 14. Next steps

VPS recommendation will be made in a follow-up step after measuring
a realistic procurement dataset. This toolkit provides the measurement
and forecasting mechanism; the actual data must come from production
or a representative load test.
