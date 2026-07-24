# R9 P2 backup and restore

Status: `R9_P2_BACKUP_RESTORE_SOURCE_CI_AND_EVIDENCE_ALIGNED`.

Source/evidence commit: `c15e5cea583f0e7553b35b91d7e719c37bfaebea`.

CI evidence: `output/r9-backup-restore-20260724T160956Z` from workflow run `30107919148`, artifact `r9-operational-hardening-evidence-c15e5cea583f0e7553b35b91d7e719c37bfaebea` (artifact digest `sha256:6d93af5ad3ff6942961961a79965561115174fd75a837f26eaee5f47b6c29b43`).

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

## Final acceptance matrix

| Scenario | Verified result |
| --- | --- |
| Consistent DB + filesystem restore | Restored DB identities, filesystem hashes and final PDF download equal the source. |
| DB-only restore | Final PDF download returns 409; no filesystem generation is recreated. |
| Filesystem-only restore | Existing filesystem bytes remain, unknown case returns 404, and no DB binding/artifact is imported. |
| Cross-tenant restore mismatch | Restore is rejected before database or filesystem mutation. |

## Final evidence

The CI runtime completed in 37.59 seconds with status `R9_P2_BACKUP_RESTORE_FAIL_CLOSED` and all five assertions true:

- backup manifest verified;
- consistent PostgreSQL plus filesystem restore reproduced source DB identities, file hashes and final PDF download;
- DB-only restore failed closed without recreating filesystem generations;
- filesystem-only restore failed closed without importing DB ownership;
- cross-tenant mismatch was rejected before target mutation;
- cleanup complete with no remaining Compose containers, networks or volumes;
- hygiene PASS with no hits;
- exactly 10 evidence files covered by 10 valid `SHA256SUMS` entries.

The operational procedure and failure handling are documented in `docs/runbooks/r9-recovery.md`. Workflow run `30107919148` completed all five CI jobs successfully; quality completed both `make check` and the full `make test` suite. Tenant-selective restore and automatic mismatch repair remain deliberately unsupported.
