# R9.0 runtime startup audit

`src.main` loads cached `Settings` at import time.  `src.shared.db.session`
also creates its SQLAlchemy engine at import time from those settings.  A child
process must therefore receive its disposable environment before importing
either module.  `src.tender_research.config` consumes the same cached settings.

The R9.0A probe uses the R8 PostgreSQL compose file, runs Alembic to the actual
database head, and starts `sys.executable -m uvicorn src.main:app` in the
repository root.  A separate Python configuration subprocess verifies that
settings and the already-created session engine have the same redacted target.

`/health` is the public liveness endpoint and is deliberately the startup
gate. `/openapi.json` may be protected when pilot auth is enabled, so its status
is recorded but is not a liveness criterion. `/health/ready` only checks that
the configured data directory exists and is a directory; it is not a database
readiness check.

The removed R8 restart attempts could report a generic healthcheck error while
leaving empty backend/result logs. The probe checks `Popen.poll()` on every
iteration and persists command output plus the backend log, so early process
exit, migration failure, bad settings, and timeout are distinguishable.

The executed probe result and evidence path are recorded by the command output
and `output/r9-uvicorn-startup-probe-*/startup-probe.json`. A passing probe
excludes the baseline hypotheses of incorrect inherited auth, wrong disposable
database/data-root configuration, import-time engine targeting, and basic
uvicorn startup failure. It does not verify application restart, PostgreSQL
restart, publication concurrency, interrupted-state recovery, or backup and
restore.
