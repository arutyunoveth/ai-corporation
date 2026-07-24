# R9 P2 backup and restore

Status: `R9_P2_BACKUP_RESTORE_SOURCE_PENDING_CI`.

R9 introduces quiesced whole-system backup and restore tooling for PostgreSQL plus the Arvectum data directory. The two stores are treated as one recovery unit.

## Contract

- Backup requires an explicit `--quiesced` acknowledgement.
- PostgreSQL is captured with `pg_dump --format=custom`.
- Filesystem data is validated to reject symlinks and unsupported objects, archived beneath `data/`, and hashed.
- A manifest binds dump hash, filesystem hash and tenant scope.
- Backup publication uses a hidden staging directory followed by atomic rename and fsync.
- Restore validates exact files, hashes, tenant scope, an empty database and an absent or empty data directory before mutation.
- Archive extraction rejects traversal, symlinks, hard links and device entries.
- Consistent restore stages filesystem bytes, restores PostgreSQL, and atomically installs the data directory.

## Acceptance matrix

| Scenario | Required result |
| --- | --- |
| Consistent DB + filesystem restore | Restored DB identities, filesystem hashes and final PDF download equal the source. |
| DB-only restore | Final PDF download returns 409; no filesystem generation is recreated. |
| Filesystem-only restore | Existing filesystem bytes remain, unknown case returns 404, and no DB binding/artifact is imported. |
| Cross-tenant restore mismatch | Restore is rejected before database or filesystem mutation. |

The CI acceptance run must finish with `R9_P2_BACKUP_RESTORE_FAIL_CLOSED`, all five assertions true, cleanup complete, hygiene PASS and 10 valid evidence checksums.

The operational procedure and failure handling are documented in `docs/runbooks/r9-recovery.md`. Tenant-selective restore and automatic mismatch repair are deliberately not implemented.
