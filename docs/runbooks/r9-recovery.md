# R9 recovery runbook

## Scope

This runbook covers whole-system recovery of the PostgreSQL database and `AI_CORP_ARVECTUM_DATA_DIR`. The two stores form one trust boundary: a database-only or filesystem-only restore is intentionally unsupported as a successful recovery mode.

The tooling is `scripts/ops/r9_recovery.py`.

## Safety rules

1. Stop all application, worker and scheduler processes before backup or restore.
2. Confirm no process can write to PostgreSQL or the data directory.
3. Pass `--quiesced` only after that confirmation.
4. Store the completed backup directory on storage with access control and independent retention.
5. Never edit `manifest.json`, `database.dump` or `filesystem.tar`.
6. Restore only into an empty PostgreSQL database and an absent or empty data directory.
7. Verify the expected tenant set before mutation.
8. Do not use filesystem presence to recreate DB ownership and do not delete orphan generations automatically.

## Backup

```bash
python scripts/ops/r9_recovery.py backup \
  --database-url "$AI_CORP_DATABASE_URL" \
  --data-dir "$AI_CORP_ARVECTUM_DATA_DIR" \
  --output-dir /secure/arvectum-backups \
  --quiesced
```

The command writes a staging directory and atomically renames it after `pg_dump`, filesystem archive creation, manifest generation and fsync complete.

A valid backup contains exactly:

- `database.dump` — PostgreSQL custom-format dump;
- `filesystem.tar` — archive rooted at `data/`;
- `manifest.json` — format version, hashes and tenant scope.

Verify it independently:

```bash
python scripts/ops/r9_recovery.py verify \
  --backup-dir /secure/arvectum-backups/<backup-id>
```

## Consistent restore

Create an empty PostgreSQL database and choose an absent or empty target data directory. Keep the application stopped.

```bash
python scripts/ops/r9_recovery.py restore \
  --database-url "$RESTORE_DATABASE_URL" \
  --data-dir "$RESTORE_DATA_DIR" \
  --backup-dir /secure/arvectum-backups/<backup-id> \
  --expected-tenants customer-a,customer-b \
  --quiesced
```

The restore performs all preflight checks before mutation, extracts the filesystem archive into a safe staging directory, restores PostgreSQL, atomically installs the data directory and writes a restore receipt beside the target directory.

After restore:

1. Run Alembic head verification without applying a new migration.
2. Start one application instance.
3. Check `/health` and `/health/ready`.
4. Download at least one previously published final PDF for every restored tenant.
5. Verify review/client-ready/delivered state for sampled cases.
6. Keep the source system stopped until verification completes.

## Failure modes

### Database restored, filesystem missing

Expected behavior is fail-closed: canonical and artifact verification returns conflict and no immutable directory is recreated. Stop the application and repeat the complete restore into new empty targets.

### Filesystem restored, database missing

Expected behavior is fail-closed: unknown cases/runs are not discovered from directories, no ownership is imported, and no orphan is deleted. Stop the application and repeat the complete restore into new empty targets.

### Tenant scope mismatch

The restore command rejects the backup before DB or filesystem mutation. Confirm the backup manifest and the intended target tenant set. There is no tenant-selective restore in R9.

### Restore interrupted after DB restore

Treat the target as DB-only mismatch. Do not start production traffic and do not copy files manually into place. Drop the target database, remove the empty target directory, and repeat the complete restore.

### Restore interrupted after filesystem staging

Staging directories use a hidden `.restore.` prefix and are not authoritative. With the application stopped, remove the staging directory only after confirming the final target was not installed, then repeat the complete restore.

## Prohibited actions

- restoring into a non-empty database;
- restoring over a populated data directory;
- changing tenant IDs in a manifest;
- importing DB rows from filesystem metadata;
- deleting orphan canonical or artifact generations as cleanup;
- mixing files from one backup with a database dump from another;
- running backup or restore while application writes are possible.
