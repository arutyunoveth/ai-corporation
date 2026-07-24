# R9 P2 backup and restore

Status: `R9_P2_BACKUP_RESTORE_REMOTE_AUDIT_CORRECTED_SOURCE_CI_AND_EVIDENCE_ALIGNED`.

Source/evidence commit: `726080a08c7b97f572b12285012667ac6a985921`.

CI evidence: `output/r9-backup-restore-20260724T193436Z` from workflow run `30120854910`, artifact `r9-operational-hardening-evidence-726080a08c7b97f572b12285012667ac6a985921` (artifact digest `sha256:c7bd35784dec4a5c95410a2739b16171a5c615b15892dbbcd818812109bc800d`).

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
- PostgreSQL restore uses `--single-transaction` and `--exit-on-error`.
- Consistent restore stages filesystem bytes, restores PostgreSQL, atomically installs the data directory and fsyncs the restore receipt.
- Expected and unexpected CLI failures return sanitized JSON without traceback or external command stderr/credentials.

## Final acceptance matrix

| Scenario | Verified result |
| --- | --- |
| Consistent DB + filesystem restore | Restored DB identities, filesystem hashes and final PDF download equal the source. |
| DB-only restore | Final PDF download returns 409; no filesystem generation is recreated. |
| Filesystem-only restore | Existing filesystem bytes remain, unknown case returns 404, and no DB binding/artifact is imported. |
| Cross-tenant restore mismatch | Restore is rejected before database or filesystem mutation. |

## Remote audit correction

The post-completion audit found that the initial recovery implementation referenced `sys.stderr` without importing `sys`, followed top-level backup symlinks after `resolve()`, ignored unexpected directories, accepted weakly validated manifest identities, exposed raw external-tool stderr, permitted restore without an explicit expected tenant set, and restored PostgreSQL without a single transaction.

The corrected source rejects those states before mutation. Focused tests cover sanitized expected failures, malformed manifests, symlink and non-file backup entries, malicious receipt-path backup identities, mandatory expected tenant scope, suppression of credential-bearing subprocess stderr, and the exact transactional `pg_restore` invocation.

## Final evidence

The CI runtime completed in 37.71 seconds with status `R9_P2_BACKUP_RESTORE_FAIL_CLOSED` and all five assertions true:

- backup manifest verified;
- consistent PostgreSQL plus filesystem restore reproduced source DB identities, file hashes and final PDF download;
- DB-only restore failed closed without recreating filesystem generations;
- filesystem-only restore failed closed without importing DB ownership;
- cross-tenant mismatch was rejected before target mutation;
- cleanup complete with no remaining Compose containers, networks or volumes;
- hygiene PASS with no hits;
- exactly 10 evidence files covered by 10 valid `SHA256SUMS` entries.

The operational procedure and failure handling are documented in `docs/runbooks/r9-recovery.md`. Workflow run `30120854910` completed all five CI jobs successfully. Quality completed `make check` and `make test`; the full suite reported 1679 passed and 188 skipped. Tenant-selective restore and automatic mismatch repair remain deliberately unsupported.