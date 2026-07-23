# R9 Operational Hardening

## P0

- application restart smoke;
- PostgreSQL restart smoke;
- idempotent artifact publication;
- identical publication concurrency;
- conflicting publication concurrency.

## P1

- interrupted canonical and artifact publication;
- DB/filesystem mismatch;
- orphan generation handling;
- review/lifecycle inconsistency.

## P2

- PostgreSQL dump plus filesystem backup;
- consistent restore;
- DB-only and filesystem-only restore mismatch;
- cross-tenant restore mismatch;
- recovery runbook.
