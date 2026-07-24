# R9 P2 backup and restore

Status: `R9_P2_BACKUP_RESTORE_CROSS_STORE_COMPENSATION_VERIFIED`.

Corrective implementation commit: `245b3f3dd65d2400a2ce4ba61d53dea6f19ef9a9`.

Main-synchronized source baseline: `5b026e7ebcae6e43257968f7609fbd45e4ba1da1`.

CI evidence for the corrective implementation: workflow run `30124640673`, all five jobs successful. The quality job completed `make check` and `make test`; the full suite reported 1680 passed and 188 skipped. Evidence artifact: `r9-operational-hardening-evidence-e1015bb927393c3f3f514c2492836bf320b329d7`, digest `sha256:94df6cd7d859a8f9ff4c18196e3bee9b573e68f66204377a605111dd0fae8b8f`.

R9 introduces quiesced whole-system backup and restore tooling for PostgreSQL plus the Arvectum data directory. The two stores are treated as one recovery unit.

## Contract

- Backup requires an explicit `--quiesced` acknowledgement.
- PostgreSQL is captured with `pg_dump --format=custom`.
- Filesystem data is validated to reject symlinks and unsupported objects, archived beneath `data/`, and hashed.
- A strict manifest binds dump hash, filesystem hash, UTC timestamp, constrained backup identity and tenant scope.
- A backup directory must contain exactly three regular non-symlink files; extra files, directories and top-level symlinks are rejected.
- Backup publication uses a hidden staging directory followed by atomic rename and fsync.
- Restore requires an explicit expected tenant set and validates exact files, hashes, tenant scope, an empty database and an absent or empty data directory before mutation.
- Archive extraction rejects traversal, duplicate normalized paths, symlinks, hard links and device entries.
- The staged filesystem is atomically installed and its parent directory is fsynced before PostgreSQL restoration begins.
- PostgreSQL restore uses `--single-transaction` and `--exit-on-error`.
- If PostgreSQL restoration fails while the recovery process is still running, the newly installed filesystem is removed, the target directory is returned to its original absent-or-empty state, the parent directory is fsynced, and no restore receipt is written.
- A restore receipt is written and fsynced only after both filesystem installation and PostgreSQL restoration succeed.
- Expected and unexpected CLI failures return sanitized JSON without traceback or external command stderr/credentials.

The implementation does not claim a distributed transaction across PostgreSQL and the filesystem. A process or node crash after filesystem installation but before compensation can still leave a filesystem-only target. That state remains fail-closed: filesystem presence cannot establish database ownership, and no successful receipt exists.

## Final acceptance matrix

| Scenario | Verified result |
| --- | --- |
| Consistent DB + filesystem restore | Restored DB identities, filesystem hashes and final PDF download equal the source. |
| Database restore failure after filesystem installation | The filesystem is visible during the attempted DB restore, then rolled back to the original empty target; no staging directory or receipt remains. |
| DB-only restore | Final PDF download returns 409; no filesystem generation is recreated. |
| Filesystem-only restore | Existing filesystem bytes remain, unknown case returns 404, and no DB binding/artifact is imported. |
| Cross-tenant restore mismatch | Restore is rejected before database or filesystem mutation. |

## Remote audit corrections

The first post-completion audit found that the initial recovery implementation referenced `sys.stderr` without importing `sys`, followed top-level backup symlinks after `resolve()`, ignored unexpected directories, accepted weakly validated manifest identities, exposed raw external-tool stderr, permitted restore without an explicit expected tenant set, and restored PostgreSQL without a single transaction.

A later cross-store audit found another unresolved boundary: `restore_backup()` committed PostgreSQL before installing the filesystem, so interruption between those operations could leave a DB-only target. Regression test `tests/test_r9_recovery_security.py::test_restore_rolls_back_installed_filesystem_when_database_restore_fails` proved the required sequence and compensation behavior. The implementation now installs the filesystem first and compensates it if transactional PostgreSQL restoration fails.

Focused security coverage includes sanitized expected failures, malformed manifests, symlink and non-file backup entries, malicious receipt-path backup identities, mandatory expected tenant scope, suppression of credential-bearing subprocess stderr, the exact transactional `pg_restore` invocation, and filesystem compensation after an injected database restore failure.

## Final evidence

The backup/restore acceptance runtime completed in 37.45 seconds with status `R9_P2_BACKUP_RESTORE_FAIL_CLOSED` and all five acceptance assertions true:

- backup manifest verified;
- consistent PostgreSQL plus filesystem restore reproduced source DB identities, file hashes and final PDF download;
- DB-only restore failed closed without recreating filesystem generations;
- filesystem-only restore failed closed without importing DB ownership;
- cross-tenant mismatch was rejected before target mutation;
- cleanup completed with no remaining Compose containers, networks or volumes;
- hygiene passed with no hits;
- exactly 10 evidence files were covered by 10 valid `SHA256SUMS` entries.

The operational procedure and failure handling are documented in `docs/runbooks/r9-recovery.md`. Tenant-selective restore, automatic ownership import, and automatic mismatch repair remain deliberately unsupported.
