# R9.2 PostgreSQL stop/start persistence smoke

Implementation: current R9.2 branch head; authoritative SHA is recorded in PR #16.

Evidence: `output/r9-postgres-restart-20260723T174021Z`
Status: `R9_2_POSTGRESQL_RESTART_SMOKE_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

## PostgreSQL and volume lifecycle

The pre, stopped, and post container ID was `0488afb1db097de186c0be83feea50e493026d8b10ecd5250dce7dabda1d0216`; container name was `/r9pg35794dbdaf-postgres-1`. Pre/post health was `healthy`; stopped state remained present with `running=false` and health `unhealthy`.

StartedAt changed from `2026-07-23T17:40:22.150006813Z` to `2026-07-23T17:40:32.41794396Z`. Stop returned 0 (requested `2026-07-23T17:40:31.817936+00:00`); start returned 0 (requested `2026-07-23T17:40:32.318023+00:00`). The SQL-unavailable probe at `2026-07-23T17:40:32.141947+00:00` returned exit code 1. PostgreSQL was healthy and SQL-ready at `2026-07-23T17:40:34.862305+00:00`.

Named volume `r9pg35794dbdaf_r8-postgres-data` was preserved through all three states: CreatedAt `2026-07-23T20:40:22+03:00`, mountpoint and source `/var/lib/docker/volumes/r9pg35794dbdaf_r8-postgres-data/_data`, destination `/var/lib/postgresql/data`. Volume labels were preserved: Compose project `r9pg35794dbdaf`, volume `r8-postgres-data`, Compose version `5.3.0`, and config hash `6f3142bdd6ba4f746d5c818052bcc11339924bf33e01037c762f0e7c4b696fe1`.

Fresh SQL probes preserved database `r8_acceptance`, user `r8_acceptance`, PostgreSQL 16.14 version identity, and the PostgreSQL system identifier. Alembic stayed `096_add_r8_canonical_snapshot_binding`.

## Application and customer result

First uvicorn PID `13784` was healthy (200), exited before PostgreSQL stop, and returned `-15` / `SIGTERM`. Second PID `13971` started after SQL readiness, returned health 200, and exited `-15` / `SIGTERM`. The stopped first process made `/health` unavailable.

HTTP identity was preserved: delivered case `4d6e26cc-b2c2-43db-8029-eb71896d48fe`, project `59ed0d8b-1721-432e-ba15-d6f391b9b4f9`, one completed run `053e9f1e-2b0a-4e8d-8287-2ee0a3628995`, and one published final artifact `9650d0e0-79e0-4421-a8d7-00f2e2ba91c0` / `3514949a876d29b57967a38f`.

Pre/post PDF SHA-256 was `374733086dc26b15b7254797592313a3c58f58845333cc861df2ec0740d08d2a`, byte size `38605`, matching the PostgreSQL `PilotArtifact` binding. Database and normalized filesystem snapshots matched; fresh canonical, artifact, and review verifier subprocesses passed before and after.

## Evidence finalization

The post-restart operation ledger has eight read-only entries: `alembic_revision` (SELECT), `health` (GET), `case` (GET), `artifacts` (GET), `final_pdf` (GET), `database_snapshot` (SELECT), `filesystem_snapshot` (SELECT), and `verifiers` (SELECT). No mutation methods occurred.

All 51 assertions were true. Both hygiene scans returned no hits. Cleanup errors were empty; Compose down returned 0 and containers, volumes, networks, and temporary directory were absent. `SHA256SUMS` contains 14 entries, excludes itself, and all 14 hashes were recalculated successfully.

This stage does not test application connection-pool recovery during outage, publication concurrency/idempotency, interrupted states, recovery commands, or backup/restore.
