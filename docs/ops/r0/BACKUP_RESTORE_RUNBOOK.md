# Backup and restore runbook

## Create a backup

Run from the canonical product checkout. The script creates a timestamped directory outside Git, captures every registered worktree, and never resets, cleans, deletes, or modifies a checkout.

```bash
ARVECTUM_POSTGRES_DB=arvectum \
ARVECTUM_POSTGRES_HOST=127.0.0.1 \
ARVECTUM_POSTGRES_PORT=55432 \
./scripts/ops/backup_arvectum.sh
```

The environment must supply authentication for PostgreSQL by its normal local mechanism. Do not put credentials on the command line or in shell history.

## Verify without restore

```bash
./scripts/ops/verify_backup.sh /absolute/path/to/backup
```

Verification checks the Git bundle, data archive, PostgreSQL dump indexes, and file hashes. It does not touch a database.

## Restore safely

1. Create a new empty checkout and verify its remotes before restoring patches.
2. Restore Git history into that separate checkout:

   ```bash
   git clone /absolute/path/to/ai-corporation-all-refs.bundle recovered-ai-corporation
   ```

3. Review `tracked-diff.patch`, `staged-diff.patch`, and the untracked archive from the relevant checkout before applying any of them.
4. Extract runtime data only into a new, non-production directory and inspect ownership and paths:

   ```bash
   tar -xzf runtime-data.tar.gz -C /safe/recovery/path
   ```

5. Restore PostgreSQL only into a newly created recovery database, never the active production database:

   ```bash
   createdb arvectum_recovery_$(date +%Y%m%d)
   pg_restore --dbname=arvectum_recovery_YYYYMMDD postgres.dump
   ```

6. Run migrations/status checks and application smoke tests against the recovery database before any cutover.

## R0.01 verified backup

`/Users/master/Documents/arvectum-r0-backups/20260711-145008` was verified on 2026-07-11 with `git bundle verify`, `tar -tzf`, and `pg_restore --list`. Its local environment archive is permission-restricted and intentionally omitted from Git.
