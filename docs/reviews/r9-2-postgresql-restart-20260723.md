# R9.2 PostgreSQL stop/start persistence smoke

Commit: `4c9ddfd45710c62c4c08c05a8079a220e53a1b04`  
Evidence: `output/r9-postgres-restart-20260723T173102Z`  
Status: `R9_2_POSTGRESQL_RESTART_SMOKE_PASS_LOCAL_FAIL_CLOSED_EVIDENCE`

The same PostgreSQL container `88f2e689e3c130e936acc651ebbc4ad2c03a659f9c649dce23fb0369f1f943a5` was stopped and started. StartedAt changed from `2026-07-23T17:31:02.959504605Z` to `2026-07-23T17:31:12.345159517Z`; the named volume `r9pg8553c75c16_r8-postgres-data`, mountpoint, labels, and mount binding were preserved. SQL was unavailable while stopped (probe exit 1), then ready after start; database/user and `pg_control_system()` system identifier remained unchanged.

PostgreSQL stop/start commands both returned 0. Stop requested at `2026-07-23T17:31:11.707618+00:00`; start requested at `2026-07-23T17:31:12.199227+00:00`; healthy and SQL-ready at `2026-07-23T17:31:14.924556+00:00`.

Application PIDs were `10027` and `10218`, both stopped with `-15`/SIGTERM. The first had exited before PostgreSQL stop; the second started after SQL readiness. Pre/post HTTP case and artifact responses were 200, preserving one delivered case, one completed run, and one final artifact. PDF SHA-256 was `e7fa19a579806b969d0ab44a2a592e7d0ece8cd13a37f169d89061ae371931ca`, byte size `38605`, matching `PilotArtifact`.

Database and normalized filesystem snapshots were equal; fresh canonical, artifact, and review verifiers passed before and after. All 44 assertions were true. Hygiene self-test and final scan passed; cleanup removed all Compose resources and temporary data. `SHA256SUMS` was generated after final result writing.

This stage does not cover application pool recovery during outage, publication concurrency/idempotency, interrupted states, recovery commands, or backup/restore.
