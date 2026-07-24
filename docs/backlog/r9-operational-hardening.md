# R9 Operational Hardening

Status: `R9_OPERATIONAL_HARDENING_REMOTE_AUDIT_CORRECTED_SOURCE_CI_EVIDENCE_AND_RUNBOOK_ALIGNED`.

Final verified source/evidence baseline: `726080a08c7b97f572b12285012667ac6a985921`.

Final source CI: workflow run `30120854910`, all five jobs successful. The quality job completed `make check` and `make test`; the full suite reported 1679 passed and 188 skipped tests. R9 evidence was published as artifact `r9-operational-hardening-evidence-726080a08c7b97f572b12285012667ac6a985921`, digest `sha256:c7bd35784dec4a5c95410a2739b16171a5c615b15892dbbcd818812109bc800d`.

## P0 — completed

- [x] application restart smoke;
- [x] PostgreSQL restart smoke;
- [x] idempotent artifact publication;
- [x] identical publication concurrency;
- [x] conflicting publication concurrency.

## P1 — completed

- [x] interrupted canonical and artifact publication — `docs/reviews/r9-5-interrupted-publication-20260724.md`;
- [x] DB/filesystem mismatch characterization and fail-closed remediation — `docs/reviews/r9-5b-db-filesystem-mismatch.md`;
- [x] deterministic filesystem-only canonical and final-PDF ownership rejection — `docs/reviews/r9-5c-orphan-lifecycle.md`;
- [x] orphan generation handling — `docs/reviews/r9-5c-orphan-lifecycle.md`;
- [x] review/lifecycle inconsistency — `docs/reviews/r9-5c-orphan-lifecycle.md`.

## P2 — completed

- [x] PostgreSQL custom-format dump plus filesystem backup;
- [x] strict backup file-set, manifest, hash, identity and archive-path validation;
- [x] explicit expected tenant scope before restore mutation;
- [x] transactional PostgreSQL restore with `--single-transaction` and `--exit-on-error`;
- [x] consistent restore;
- [x] DB-only and filesystem-only restore mismatch;
- [x] cross-tenant restore mismatch;
- [x] sanitized recovery CLI failures;
- [x] recovery runbook — `docs/runbooks/r9-recovery.md`;
- [x] source/evidence review — `docs/reviews/r9-p2-backup-restore.md`.

## Remote source audit corrections

The independent post-completion GitHub audit found and corrected two safety classes that the original acceptance evidence did not fully prove:

1. A deterministic renderer could reproduce an existing filesystem-only final-PDF generation and recreate a `PilotArtifact` DB binding. Publication is now serialized at the DB binding boundary, concurrent candidates are compared by hash and size, and an idempotent generation without a DB row is explicitly rejected.
2. Recovery failure handling and validation were incomplete: missing `sys` import on error output, top-level symlink following, ignored non-file backup entries, weak manifest and backup-ID validation, optional tenant scope, raw external-tool stderr and non-transactional `pg_restore`. These paths now fail closed and have focused regression tests.

## Final R9 guarantees

- immutable canonical and final-PDF publication remains fail-closed under restart, concurrency and interruption;
- filesystem-only canonical or artifact data never establishes database ownership, including deterministic byte-identical retries;
- identical concurrent publication remains idempotent and conflicting candidate bytes return 409;
- orphan generations are preserved for diagnosis and are not imported or deleted automatically;
- review and lifecycle transitions require the verified current run, artifact and review binding;
- PostgreSQL and filesystem backups form one explicitly quiesced recovery unit with strict hash, identity, archive-path and tenant-scope validation;
- restore requires an explicit expected tenant inventory and uses transactional PostgreSQL restoration;
- DB-only, filesystem-only and cross-tenant restore mismatches fail closed;
- expected and unexpected recovery CLI failures are sanitized;
- no automatic repair, tenant-selective restore, ownership import or orphan deletion is introduced.

PR #16 remains Draft. R9 is complete and independently corrected on the remote branch but is not merged by this document.