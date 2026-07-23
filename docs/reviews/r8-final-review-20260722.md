# R8 tenant acceptance review

## Current assessment

`R8_CUSTOMER_PILOT_WORKSPACE_ACCEPTED_R9_OPERATIONAL_HARDENING_DEFERRED`.

The tenant stage records 30 real HTTP scenarios, split equally in both
directions, with foreign-leak, database, filesystem, lifecycle, audit and
cleanup assertions. Actor-owned list/read semantics and branch-SHA evidence
metadata are corrected. Publication concurrency is PENDING, not exercised by
this tenant-evidence stage. The evidence contract is fail-closed.

The dedicated PostgreSQL 095→096 stage now seeds four real tenant-scoped legacy
fixtures, captures database/filesystem snapshots, verifies fail-closed
incomplete/conflict fixtures, runs two locked concurrent backfills, exercises
the failing downgrade path, and verifies the 096→095→096 transition. Legacy
artifact trust is verified during that backfill.

The dedicated PostgreSQL/uvicorn tampering runner records the immutable 32-case
matrix: canonical filesystem 8/8, artifact filesystem 6/6, run-result DB 12/12
and artifact DB 6/6. Each case verifies both production verifiers, protected
HTTP operations fail closed, no PDF disclosure, no auto-repair, unchanged
control customer, and exact runner-owned restoration. The evidence contract was
then corrected to require recorded filesystem and DB snapshots, audit deltas,
separate review/lifecycle fixtures, branch-head SHA metadata, control download,
and cleanup evidence before it may issue PASS.

Restart, crash recovery, publication concurrency, and backup/restore are
accepted operational-hardening work for R9; they are not merge blockers for
the controlled R8 customer-pilot workspace. PostgreSQL integration, immutable
artifact binding, review/feedback/lifecycle, and accepted CI evidence are PASS.

## Required before a merge-ready recommendation

- executable R7 regression;
- R9 operational-hardening evidence.

This is not a disaster-recovery or full operational-resilience certificate.
