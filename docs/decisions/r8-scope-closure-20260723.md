# R8 Scope Closure

## Accepted R8 scope

- customer/project/case/run data model;
- tenant isolation;
- canonical result persistence;
- immutable artifact publication;
- review and feedback binding;
- lifecycle transitions;
- PostgreSQL migrations and legacy migration/backfill;
- artifact trust validation, tampering protection, audit and cleanup evidence.

## Accepted evidence

- R7 baseline: `8bb52591372475dde63dc32260cd2a0c4cf0e422`;
- tenant stage: 30/30 PASS;
- migration/backfill and legacy artifact trust: PASS;
- tampering stage: 32/32 PASS;
- combined DB tampering subchecks: 16/16 PASS;
- accepted R8 branch head: `6fbbe16c94ce8867f3ac36bf1a6cc7fc08a55475`.

## Deferred to R9

- clean application and PostgreSQL restart;
- interrupted-state recovery and uncertain-result idempotency;
- identical/conflicting publication concurrency;
- PostgreSQL plus filesystem backup, restore, mismatch detection, and recovery runbook;
- continuous recovery CI.

## Risk acceptance

Restart, recovery, and backup are not claimed as verified. R8 is not a
disaster-recovery release, but the customer workspace is accepted for a
controlled pilot. Operations require normal completion and operator-managed
backup until R9. Corrupted immutable bindings fail closed; automatic recovery
is deliberately not implemented.

## Decision

`R8_CUSTOMER_PILOT_WORKSPACE_ACCEPTED_R9_OPERATIONAL_HARDENING_DEFERRED`
