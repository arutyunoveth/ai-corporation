# ARV-009 R8 Compatibility

## R8 Merge

- **PR #12** merged `2026-07-23T14:02:49Z`
- **R8 merge commit**: `e0cb0ffdf0f10c75fb92f74be698c61f4f32cdce`
- **R8 Alembic head**: `096_add_r8_canonical_snapshot_binding`
- **Main branch SHA at verification**: `e0cb0ffdf0f10c75fb92f74be698c61f4f32cdce`

## Accepted ARV-009 Baseline

- **Branch**: `opencode/ops-storage-sizing`
- **Accepted commit**: `701520e62f7a0dd9ba25515b725a3aff5c769c64`
- **After rebase**: SHA `615cb85a5fd98a4ce98f3989dcac5b50d870cfcc` (3 commits preserved)

## Storage-Bearing Relations

The following R8 tables are dynamically detected by the pg_catalog-based collector:

| Table | Type | Vector Columns | TOAST | R8 Migration |
|-------|------|---------------|-------|-------------|
| `pilot_projects` | user | none | yes | 093 |
| `procurement_cases` | user | none | yes | 093 |
| `pilot_reviews` | user | none | yes | 093 |
| `pilot_feedback` | user | none | yes | 093 |
| `pilot_audit_events` | user | none | yes | 093 |
| `pilot_run_results` | user | none | yes | 094 |
| `pilot_artifacts` | user | none | yes | 094 |

The collector uses `pg_total_relation_size`, `pg_indexes_size`, and `pg_table_size` — no hardcoded table names. Any future tables added to `public` schema are automatically included.

## R8 Filesystem Roots

| Root Name | Container Path | Purpose | Backup Source |
|-----------|---------------|---------|--------------|
| `data` | `/app/data` | Canonical snapshots, exports | yes |
| `artifacts` | `/app/artifacts` | Final PDF artifacts | yes |
| `eis-archives` | `/app/eis-archives` | EIS SOAP archives | yes |

## Alias Mounts

| Name | Container Path | Aliased To | Docker Volume |
|------|---------------|-----------|--------------|
| `company-agent-runs` | `/app/company_agent_runs` | `artifacts` (same `pilot-artifacts` volume) | `pilot-artifacts` |

The capacity toolkit detects alias mounts by comparing `storage_identity_id` (derived from `stat.st_dev` + `stat.st_ino`). Aliases are marked `counted_in_totals=false`.

## Backup Coverage

Backup (`deploy/pilot/scripts/backup.sh`) includes:
- `database.dump` — `pg_dump -Fc` of entire database
- `artifacts.tar.gz` — tar of `data/`, `artifacts/`, `eis-archives/`
- `manifest.json` — SHA256 manifest with Alembic head
- `SHA256SUMS` — checksums of all backup files

## PII / Privacy Boundaries

The capacity toolkit never outputs:
- Absolute filesystem paths
- Database connection strings or passwords
- Customer names, INN, KPP, or procurement numbers
- Synthetic entity values used during testing

## Synthetic R8 Snapshot Command

```bash
# PostgreSQL connection (psycopg, not SQLAlchemy format)
export AI_CORP_DATABASE_URL='postgresql://user:password@host:port/dbname'

# Full snapshot with R8 roots
python scripts/capacity/arv_capacity.py snapshot \
  --database-url-env AI_CORP_DATABASE_URL \
  --root 'data=/path/to/data' \
  --root 'artifacts=/path/to/artifacts' \
  --root 'eis-archives=/path/to/eis-archives' \
  --root 'company-agent-runs=/path/to/artifacts' \
  --backup-source-root data \
  --backup-source-root artifacts \
  --backup-source-root eis-archives \
  --backup-dir /path/to/backup \
  --output-dir /path/to/snapshot
```

## Controlled Real-Data Snapshot Command (future)

```bash
python scripts/capacity/arv_capacity.py snapshot \
  --database-url-env AI_CORP_PROD_DATABASE_URL \
  --root 'data=/app/data' \
  --root 'artifacts=/app/artifacts' \
  --root 'eis-archives=/app/eis-archives' \
  --root 'company-agent-runs=/app/company_agent_runs' \
  --backup-source-root data \
  --backup-source-root artifacts \
  --backup-source-root eis-archives \
  --backup-dir /path/to/prod/backup \
  --output-dir /path/to/output
```

## Acceptance (ARV-009B1)

- **Clean venv**: Python 3.11.15, pip 26.1.2
- **Capacity tests**: 65 passed, 1 skipped
- **Full test suite**: 1577 passed, 187 skipped
- **`make check`**: all passed
- **Secret scan**: clean
- **Alembic head**: `096_add_r8_canonical_snapshot_binding` (single head)
- **PostgreSQL**: 16.14 + pgvector 0.8.5 (Docker, disposable)
- **R8 migrations**: all 96 applied, idempotent
- **Snapshot**: `read_only_verified=true`, all 7 R8 tables detected, 1320 indexes measured, alias deduplication confirmed
- **Forecast**: measured baseline, projected = baseline + incremental, 3 profiles, 3 formats consistent
- **Privacy**: no DSN, password, absolute paths, or synthetic PII in output

## Limitations

- **Real customer data was not measured during ARV-009B1.**
- **No final VPS recommendation was produced.**
- Synthetic data uses random/placeholder content; real-world volumes will differ.
- The R8 `procurement_document_embeddings` table stores embedding references externally; no vector columns exist in the current R8 schema.
