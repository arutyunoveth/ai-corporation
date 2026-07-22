# R8 final independent review

## Scope

- Head reviewed: `9fe7c13b624eb02d3096860ad48855decab12dd8`
- Base reviewed: `8bb52591372475dde63dc32260cd2a0c4cf0e422`
- PR: #12 (Draft)

## Findings

### Verified

- The current tracked worktree is clean; the only local change is the allowed
  untracked Compose override.
- `096_add_r8_canonical_snapshot_binding` is the single Alembic head.
- The canonical snapshot, PDF artifact, and review verifiers follow filesystem
  bytes through immutable manifests into DB bindings rather than accepting a
  caller-supplied hash.
- R8 exact-byte PDF download is served from the verified artifact binding.
- The retained isolated PostgreSQL evidence shows two concurrent final-PDF HTTP
  publications returning one immutable artifact identity without HTTP 500.
- Customer input identities are content-derived and no longer depend on a
  generated document UUID. Document role detection is in a neutral module and
  the customer resolver has no demo-module import.
- `make test-r8-postgres` starts a disposable PostgreSQL 16+pgvector service,
  runs migrations, exercises two independent FastAPI request/session
  boundaries, verifies the single published artifact, and tears the service
  down in `finally`. GitHub Actions run `29942467649` completed this job.

### Blocking gaps

1. The acceptance evidence directory retains only four of the fourteen
   required files. It lacks lifecycle, migration-cycle, tenant-isolation,
   restart, tampering, inventory, DB-count, commands, and checksum evidence.
2. The required 095→096→095→096 migration cycle and the full tampering/lifecycle
   matrices have not been supplied as reproducible test evidence.

## Recommendation

**REVIEW_CHANGES_REQUIRED**. The PostgreSQL concurrency regression coverage is
now reproducible, but the missing full evidence matrix and migration cycle
still prevent a `MERGE_READY` recommendation. No merge, tag, deployment, or
auto-merge action was performed by this review.
