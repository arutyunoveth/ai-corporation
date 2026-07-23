# R8 isolated Compose acceptance evidence (sanitized)

- Review head: `9fe7c13b624eb02d3096860ad48855decab12dd8`
- Base: `8bb52591372475dde63dc32260cd2a0c4cf0e422`
- Collected at: 2026-07-22
- Local evidence source: `output/r8-compose-acceptance-20260722-193213/`
- Compose project: `r8acceptance`
- Docker: 29.6.2; Compose: v5.3.0; Python: 3.14.6
- CI: GitHub Actions run `29939576906` (quality, migrations, security: success)
- Alembic head: `096_add_r8_canonical_snapshot_binding`
- Frozen R7 PDF SHA-256:
  `3021d1d38be7256b1c41f1f916e0652893d55f6f5edb032359c4efcc41c7fd73`

## Verified evidence

The retained `concurrency-results.json` records canonical completion followed
by two concurrent FastAPI final-PDF publication requests against the isolated
PostgreSQL backend. Both returned HTTP 201 for the same artifact ID and key;
both returned the same PDF SHA-256
`3e17c043c5fec3b5e90e3a33e86d063200ecae51048173a44bdb75c144615e41`.
The acceptance note records teardown of the `r8acceptance` containers and
volumes without touching pre-existing containers.

## Evidence limitations

This report deliberately does not claim evidence that is not retained. The
source directory currently lacks the requested commands log, migration state,
lifecycle result, tenant-isolation result, tampering result, artifact
inventory, database counts, and SHA summary. Therefore it is a sanitized
record of the concurrency exercise, not a complete acceptance certificate.

No credentials, tokens, headers, cookies, env-file values, or production
hostnames are included here.
