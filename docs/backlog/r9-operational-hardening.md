# R9 Operational Hardening

Status: `R9_OPERATIONAL_HARDENING_COMPLETE_SOURCE_CI_EVIDENCE_AND_RECOVERY_RUNBOOK_ALIGNED`.

Final verified source/evidence baseline: `c15e5cea583f0e7553b35b91d7e719c37bfaebea`.

Final source CI: workflow run `30107919148`, all five jobs successful. The quality job completed `make check` and `make test`; the full suite reported 1671 passed and 188 skipped tests. R9 evidence was published as artifact `r9-operational-hardening-evidence-c15e5cea583f0e7553b35b91d7e719c37bfaebea`, digest `sha256:6d93af5ad3ff6942961961a79965561115174fd75a837f26eaee5f47b6c29b43`.

## P0 — completed

- [x] application restart smoke;
- [x] PostgreSQL restart smoke;
- [x] idempotent artifact publication;
- [x] identical publication concurrency;
- [x] conflicting publication concurrency.

## P1 — completed

- [x] interrupted canonical and artifact publication — `docs/reviews/r9-5-interrupted-publication-20260724.md`;
- [x] DB/filesystem mismatch characterization and fail-closed remediation — `docs/reviews/r9-5b-db-filesystem-mismatch.md`;
- [x] orphan generation handling — `docs/reviews/r9-5c-orphan-lifecycle.md`;
- [x] review/lifecycle inconsistency — `docs/reviews/r9-5c-orphan-lifecycle.md`.

## P2 — completed

- [x] PostgreSQL dump plus filesystem backup;
- [x] consistent restore;
- [x] DB-only and filesystem-only restore mismatch;
- [x] cross-tenant restore mismatch;
- [x] recovery runbook — `docs/runbooks/r9-recovery.md`;
- [x] source/evidence review — `docs/reviews/r9-p2-backup-restore.md`.

## Final R9 guarantees

- immutable canonical and final-PDF publication remains fail-closed under restart, concurrency and interruption;
- filesystem-only canonical or artifact data never establishes database ownership;
- orphan generations are preserved for diagnosis and are not imported or deleted automatically;
- review and lifecycle transitions require the verified current run, artifact and review binding;
- PostgreSQL and filesystem backups form one quiesced recovery unit with hash and tenant-scope validation;
- DB-only, filesystem-only and cross-tenant restore mismatches fail closed;
- no automatic repair, tenant-selective restore, ownership import or orphan deletion is introduced.

PR #16 remains Draft. R9 is complete on the branch but is not merged by this document.
