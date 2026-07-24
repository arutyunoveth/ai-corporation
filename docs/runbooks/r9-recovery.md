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
7. Always supply and independently verify the complete expected tenant set. Restore without `--expected-tenants` is rejected.
8. Do not use filesystem presence to recreate DB ownership and do not delete orphan generations automatically.
9. Do not place the backup output directory behind a symlink. Use a dedicated path outside the Arvectum data directory.

## Backup

```bash
python scripts/ops/r9_recovery.py backup \
  --database-url "$AI_CORP_DATABASE_URL" \
  --data-dir "$AI_CORP_ARVECTUM_DATA_DIR" \
  --output-dir /secure/arvectum-backups \
  --quiesced
```

The command writes a mode-0700 staging directory and atomically renames it after `pg_dump`, filesystem archive creation, manifest generation and fsync complete. External command failures are returned as sanitized JSON and do not echo database credentials or raw subprocess stderr.

A valid backup contains exactly three regular, non-symlink files and no extra directory entries:

- `database.dump` — PostgreSQL custom-format dump;
- `filesystem.tar` — archive rooted at `data/`;
- `manifest.json` — strict format version, constrained backup identity, timezone-aware creation time, hashes and tenant scope.

Verify it independently:

```bash
python scripts/ops/r9_recovery.py verify \
  --backup-dir /secure/arvectum-backups/<backup-id>
```

Verification rejects malformed JSON, unknown or missing manifest fields, invalid hashes, duplicate or unsorted tenant lists, tenant-scope inconsistency, unexpected files/directories and top-level symlinks.

## Consistent restore

Create an empty PostgreSQL database and choose an absent or empty target data directory. Keep the application stopped. Determine the full tenant set from an independently verified inventory; do not copy it blindly from an untrusted manifest.

```bash
python scripts/ops/r9_recovery.py restore \
  --database-url "$RESTORE_DATABASE_URL" \
  --data-dir "$RESTORE_DATA_DIR" \
  --backup-dir /secure/arvectum-backups/<backup-id> \
  --expected-tenants customer-a,customer-b \
  --quiesced
```

The restore performs all preflight checks before mutation. It safely extracts the filesystem archive into a hidden staging directory, rejects traversal, duplicate normalized paths, symlinks, hard links and device entries, restores PostgreSQL with `pg_restore --single-transaction --exit-on-error`, atomically installs the data directory, and writes and fsyncs a restore receipt beside the target directory.

PostgreSQL and filesystem installation are not one cross-store transaction. An interruption after PostgreSQL commit but before filesystem rename is a DB-only mismatch and must be recovered according to the failure procedure below.

After restore:

1. Run Alembic head verification without applying a new migration.
2. Start one application instance.
3. Check `/health` and `/health/ready`.
4. Download at least one previously published final PDF for every restored tenant.
5. Verify review/client-ready/delivered state for sampled cases.
6. Compare the receipt tenant scope with the approved restore inventory.
7. Keep the source system stopped until verification completes.

## Failure modes

### Database restored, filesystem missing

Expected behavior is fail-closed: canonical and artifact verification returns conflict and no immutable directory is recreated. Stop the application and repeat the complete restore into new empty targets.

### Filesystem restored, database missing

Expected behavior is fail-closed: unknown cases/runs are not discovered from directories, no ownership is imported, and no orphan is deleted. Stop the application and repeat the complete restore into new empty targets.

### Tenant scope omitted or mismatched

The restore command rejects a missing or non-equal expected tenant set before DB or filesystem mutation. Confirm the independently approved tenant inventory and the verified backup manifest. There is no tenant-selective restore in R9.

### Backup verification fails

Do not repair or edit the backup in place. Preserve it for diagnosis, obtain another independently retained copy, and repeat `verify`. A checksum, schema, path or archive-policy failure makes the backup unusable for automatic restore.

### Restore interrupted after DB restore

Treat the target as DB-only mismatch. Do not start production traffic and do not copy files manually into place. Drop the target database, remove the empty target directory, and repeat the complete restore.

### Restore interrupted after filesystem staging

Staging directories use a hidden `.restore.` prefix and are not authoritative. With the application stopped, remove the staging directory only after confirming the final target was not installed, then repeat the complete restore.

## Prohibited actions

- restoring into a non-empty database;
- restoring over a populated data directory;
- omitting or guessing the expected tenant set;
- changing tenant IDs, hashes or backup IDs in a manifest;
- following backup or target symlinks;
- importing DB rows from filesystem metadata;
- deleting orphan canonical or artifact generations as cleanup;
- mixing files from one backup with a database dump from another;
- exposing raw recovery command stderr in customer-facing logs;
- running backup or restore while application writes are possible.