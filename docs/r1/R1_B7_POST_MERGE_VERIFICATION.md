# R1.B7.3 Post-merge verification

Status: `R1_MERGED_POST_MERGE_VERIFIED`

- Merge SHA: `744b96376f0a5e5baf964e15ffc11d61a7b5e924`
- Tree SHA: `75063fbcff2a0dd6e08a063ff4bd7ad205b15ac4`
- Parents: `bc5194600b9b17bd89b2bc02ce92577708a23c35` (previous main), `5ad7c71d93d6456d3bc8c96ac1a0017edb2a3a2f` (PR head)
- `origin/main` pointed to the merge SHA; no later main commit was present during verification.

## GitHub Actions

Push run `29360502819` for the merge SHA completed successfully:

- `quality`: success, job `87179044492`, 19:05:48–19:11:23 UTC
- `security`: success, job `87179044488`, 19:05:50–19:05:55 UTC
- `migrations`: success, job `87179044465`, 19:05:49–19:06:10 UTC

## Local checks

Logs: `tmp/r1/post-merge-744b963/`

- `make check`: exit 0
- `make test`: exit 0; `1370 passed, 185 skipped, 0 failed, 0 errors`
- Targeted golden/report/renderer/upload/binding set: exit 0
- FastAPI import: `FastAPI`
- `alembic heads`: `092_create_tender_analysis_jobs_table (head)`
- Secret scan: `clean`

The detached verification checkout was clean before and after checks. No production services or production database were started.

## Scope and rollback

No product code, migrations, runtime configuration, deployment assets, or tests were changed by this verification. No deploy, tag, production ingest, production migration, DNS/hosting/proxy change, or client publication was performed.

If rollback is ever required, do not move `main` backwards. Create a separate branch from current `main`, run `git revert -m 1 744b96376f0a5e5baf964e15ffc11d61a7b5e924`, open a rollback PR, run CI, and merge only after explicit owner approval.

Known limitation: this is automated post-merge verification; visual review of exported documents remains a human responsibility.
