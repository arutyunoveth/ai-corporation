# R9.1 application restart smoke

Branch: `codex/r9-operational-hardening`; frozen R8 origin:
`e0cb0ffdf0f10c75fb92f74be698c61f4f32cdce`.

The local run recorded first/second uvicorn PIDs `84916` and `85190`; the first
process stopped with `-15` after SIGTERM. Both `/health` probes and both PDF
downloads returned 200. PostgreSQL container ID, StartedAt, and RestartCount
were unchanged. Alembic remained at `096_add_r8_canonical_snapshot_binding`.

Pre/post database snapshots and filesystem snapshots were identical. Canonical,
artifact, and review bindings each returned PASS before and after restart. The
PDF SHA-256 was unchanged: `637f1f6447e4f3edffbf1a04dc768af1a196a3c63a9058038236e4b339427308`.
Cleanup removed the runner container, volume, network, and temporary directory.

The evidence pack is the authoritative record. This smoke does not restart
PostgreSQL, exercise database outage recovery, publication concurrency,
interrupted states, backup, or restore.
