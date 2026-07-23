# R9.1 application restart smoke

Branch: `codex/r9-operational-hardening`; frozen R8 origin:
`e0cb0ffdf0f10c75fb92f74be698c61f4f32cdce`.

The fail-closed local run recorded separate uvicorn processes and writes their
complete lifecycle, actual health probes, termination method, and return codes
to the evidence pack. Evidence hygiene is scanned before SHA256SUMS generation.
The prior corrected local run recorded first/second uvicorn PIDs `6310` and `6349`;
both processes stopped with `-15` after SIGTERM. Both `/health` probes, the
post-restart case/artifact requests, and both PDF downloads returned 200.
Post-stop `/health` returned connection failure. PostgreSQL container ID, StartedAt, and RestartCount
were unchanged. Alembic remained at `096_add_r8_canonical_snapshot_binding`.

Pre/post database snapshots and filesystem snapshots were identical. Canonical,
artifact, and review bindings each returned PASS before and after restart. The
PDF SHA-256 was unchanged: `8932d4d5efdfdaf419e050f86e160e07a4ca83928e3fe6b6ff2dc41e1ad9e1ea`.
Cleanup removed the runner container, volume, network, and temporary directory.

The evidence pack is the authoritative record. This smoke does not restart
PostgreSQL, exercise database outage recovery, publication concurrency,
interrupted states, backup, or restore.
