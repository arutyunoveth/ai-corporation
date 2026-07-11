# Current state

Generated 2026-07-11 UTC from local observation.

- Product branch: `codex/r0-sync-2026-07-11`; upstream baseline `8998ddb`.
- Site branch: `codex/r0-sync-2026-07-11`; R0 site commit `2b04794`.
- Migration head: `092_create_tender_analysis_jobs_table`.
- PostgreSQL: Homebrew PostgreSQL 18 listening on `127.0.0.1:5432`; target `55432` is not yet active.
- Backend: no Arvectum listener on `8001`; unrelated local service occupies `8000`.
- LLM: listener observed on `8088`; compatibility not asserted by R0.
- Embeddings: no listener on `8090`.
- launchd: no Arvectum job installed; templates validated locally.
- Focused R0.02 test suite: 156 passed. R0 security suite: 6 passed.
