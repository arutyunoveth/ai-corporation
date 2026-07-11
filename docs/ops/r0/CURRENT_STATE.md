# Current state

Generated 2026-07-11 UTC from local observation.

- Product branch: `codex/r0-sync-2026-07-11`; upstream baseline `8998ddb`.
- Site branch: `codex/r0-sync-2026-07-11`; R0 site commit `2b04794`.
- Migration head: `092_create_tender_analysis_jobs_table`.
- PostgreSQL: Docker `pgvector/pgvector:pg17` on host `127.0.0.1:55432`, pgvector `0.8.4`, Alembic head `092_create_tender_analysis_jobs_table`; Homebrew PostgreSQL 18 on `5432` preserved.
- Backend: launchd `com.arvectum.backend`, `127.0.0.1:8001`, public `/health` and protected readiness/OpenAPI verified.
- LLM: Homebrew-managed Ollama OpenAI-compatible API `127.0.0.1:11434/v1`; port `8088` is not an LLM endpoint.
- Embeddings: launchd `com.arvectum.embeddings`, `127.0.0.1:8090`, `Qwen3-Embedding-4B`, 2560-dimensional live request verified.
- Docker PostgreSQL and both Arvectum launchd services survived restart smoke.
- Focused runtime tests: 27 passed; auth/embedding/database smoke passed.
