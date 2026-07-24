# R9.1 application restart review

Status: `R9_1_APPLICATION_RESTART_SMOKE_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL`

Evidence: `output/r9-application-restart-20260723T164935Z`

## Process lifecycle

| Process | PID | Start requested | Health | Stop requested | Exited | Return code | Termination |
| --- | ---: | --- | ---: | --- | --- | ---: | --- |
| first | 84675 | 2026-07-23T16:49:42.469939+00:00 | 200 at 2026-07-23T16:49:43.841076+00:00 | 2026-07-23T16:49:44.922041+00:00 | 2026-07-23T16:49:45.105690+00:00 | -15 | SIGTERM |
| second | 85009 | 2026-07-23T16:49:45.106384+00:00 | 200 at 2026-07-23T16:49:46.481029+00:00 | 2026-07-23T16:49:47.366334+00:00 | 2026-07-23T16:49:47.541014+00:00 | -15 | SIGTERM |

The first process exited before the second start request. The direct post-stop `GET /health` result was unavailable (`None`), as required.

## Customer and artifact identity

The pre/post case response was HTTP 200 and preserved delivered case `3408630e-ae5f-471a-8499-46d3f55f4153`, customer `R9-RESTART-SYNTHETIC`, project `8a708dc6-bbcf-4c88-af59-f71c394363c0`, case artifact key `c_9d733062d542480794297581f61c933a`, and exactly one completed run `2d87321f-55a9-4959-963e-812c6995470f`.

The pre/post artifacts response was HTTP 200 with exactly one `final_pdf`: id `f80be81d-d602-40c8-b20d-3f54aeffd5b5`, key `045c8b76d1ed8df6cde60412`, status `published`, renderer `r7-persisted-pdf-v2`, and immutable timestamp `2026-07-23T16:49:44.060827+00:00`.

The PostgreSQL `PilotArtifact` binding matched HTTP metadata: run result `c8d95d12-a09d-4dca-a79d-25567961cad0`, hash `7a56c36d2bd85079998cd5939b6df7b9025eaced40a91e72f301fa02b957cd89`, byte size `38605`, and relative PDF path `customer-pilot/R9-RESTART-SYNTHETIC/8a708dc6-bbcf-4c88-af59-f71c394363c0/3408630e-ae5f-471a-8499-46d3f55f4153/2d87321f-55a9-4959-963e-812c6995470f/artifacts/045c8b76d1ed8df6cde60412/final.pdf`.

Pre/post PDF responses were HTTP 200, with identical SHA-256 `7a56c36d2bd85079998cd5939b6df7b9025eaced40a91e72f301fa02b957cd89` and byte size `38605`.

## Persistence, hygiene, and cleanup

PostgreSQL container identity stayed `7657db95af493d6e1a9c1e127b76b4858527f674a1fb9f8a426d63b57a5fde8f`; started-at stayed `2026-07-23T16:49:35.574872916Z`; restart count stayed `0`. Alembic revision was `096_add_r8_canonical_snapshot_binding` both before and after. Database, filesystem, and all three fresh verifier subprocess results (canonical, artifact, review) matched before and after.

The hygiene CLI self-test passed. The final evidence hygiene scan returned no hits. Cleanup completed: both processes exited, Compose down returned 0, and no containers, volumes, networks, or temporary directory remained. `SHA256SUMS` contains 11 evidence-file hashes and was generated after the final `restart-result.json`.

All 30 required assertions were `true`.

## R9.1 scope limitations

This evidence covers a single application-process restart with unchanged PostgreSQL, data directory, environment, and API port. It does not cover PostgreSQL restart/outage, publication concurrency or idempotency, interrupted states, recovery commands, or backup/restore.
