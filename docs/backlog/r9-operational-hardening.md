# R9 Operational Hardening

Status: `R9_OPERATIONAL_HARDENING_CROSS_STORE_COMPENSATION_IMPLEMENTED_CI_VERIFIED_AND_DOCUMENTED`.

Corrective implementation commit: `245b3f3dd65d2400a2ce4ba61d53dea6f19ef9a9`.

Main-synchronized code baseline: `5b026e7ebcae6e43257968f7609fbd45e4ba1da1`. At that baseline the R9 branch is ahead of and zero commits behind `main` (`efe182182a3a6a6299c8a384f3257fc0c9d891c6`).

Corrective source CI: workflow run `30124640673`, all five jobs successful. The quality job completed `make check` and `make test`; the full suite reported 1680 passed and 188 skipped tests. R9 evidence was published as artifact `r9-operational-hardening-evidence-e1015bb927393c3f3f514c2492836bf320b329d7`, digest `sha256:94df6cd7d859a8f9ff4c18196e3bee9b573e68f66204377a605111dd0fae8b8f`.

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
- [x] filesystem installation before DB restore plus compensation back to the original absent-or-empty target state on DB restore failure;
- [x] no successful restore receipt on compensated or interrupted failure paths;
- [x] sanitized recovery CLI failures;
- [x] recovery runbook — `docs/runbooks/r9-recovery.md`;
- [x] source/evidence review — `docs/reviews/r9-p2-backup-restore.md`.

## Remote source audit corrections

The independent post-completion GitHub audits found and corrected three safety classes that the original acceptance evidence did not fully prove:

1. A deterministic renderer could reproduce an existing filesystem-only final-PDF generation and recreate a `PilotArtifact` DB binding. Publication is now serialized at the DB binding boundary, concurrent candidates are compared by hash and size, and an idempotent generation without a DB row is explicitly rejected.
2. Recovery failure handling and validation were incomplete: missing `sys` import on error output, top-level symlink following, ignored non-file backup entries, weak manifest and backup-ID validation, optional tenant scope, raw external-tool stderr and non-transactional `pg_restore`. These paths now fail closed and have focused regression tests.
3. `restore_backup()` restored PostgreSQL before installing the filesystem, leaving a DB-only interruption window. The corrected sequence installs the staged filesystem first, invokes single-transaction PostgreSQL restore, rolls the filesystem target back if that call fails, fsyncs the compensated parent state, and writes no receipt on failure. Regression test `tests/test_r9_recovery_security.py::test_restore_rolls_back_installed_filesystem_when_database_restore_fails` covers this boundary.

## Final R9 guarantees

- immutable canonical and final-PDF publication remains fail-closed under restart, concurrency and interruption;
- filesystem-only canonical or artifact data never establishes database ownership, including deterministic byte-identical retries;
- identical concurrent publication remains idempotent and conflicting candidate bytes return 409;
- orphan generations are preserved for diagnosis and are not imported or deleted automatically;
- review and lifecycle transitions require the verified current run, artifact and review binding;
- PostgreSQL and filesystem backups form one explicitly quiesced recovery unit with strict hash, identity, archive-path and tenant-scope validation;
- restore requires an explicit expected tenant inventory and uses transactional PostgreSQL restoration;
- filesystem installation precedes DB restore and is compensated on a handled DB restore failure;
- restore receipts are emitted only after both stores succeed;
- DB-only, filesystem-only and cross-tenant restore mismatches fail closed;
- abrupt host/process loss can still leave filesystem-only state because R9 does not claim a distributed cross-store transaction; that state cannot establish ownership and is not considered a successful restore;
- expected and unexpected recovery CLI failures are sanitized;
- no tenant-selective restore, ownership import, orphan deletion or unsafe automatic cross-store reconstruction is introduced.

This document records the branch contract and evidence. GitHub PR state, merge state, post-merge CI and release-tag state are verified separately and are not implied by this file alone.
