# R8 tenant acceptance review

## Current assessment

`R8_TAMPERING_MATRIX_VERIFIED_RECOVERY_R7_REQUIRED`.

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
control customer, and exact runner-owned restoration. Recovery and executable
R7 regression remain pending.

## Required before a merge-ready recommendation

- genuine recovery and executable R7 checks;
- independent verification of the CI artifact.

PR #12 remains Draft. No merge, tag, deployment, or auto-merge was performed.
This is not a full acceptance certificate.
