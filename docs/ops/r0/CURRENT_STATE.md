# Current state

Generated 2026-07-11 UTC from local observation.

- Product main merge: `6afd2364fbd03db36d3d155c65f481b9c70a22b8`; release tag `r0-sync-2026-07-11` targets this commit.
- Site main merge: `707e6f0176b8568fa73c01a98e94db17a2c68768`; site PR #1 is merged and the R0 branch remains available.
- Migration head: `092_create_tender_analysis_jobs_table`.
- PostgreSQL: Docker `pgvector/pgvector:pg17` on host `127.0.0.1:55432`, pgvector `0.8.4`, Alembic head `092_create_tender_analysis_jobs_table`; Homebrew PostgreSQL 18 on `5432` preserved.
- Backend: launchd `com.arvectum.backend`, `127.0.0.1:8001`, public `/health` and protected readiness/OpenAPI verified.
- LLM: Homebrew-managed Ollama OpenAI-compatible API `127.0.0.1:11434/v1`; port `8088` is not an LLM endpoint.
- Embeddings: launchd `com.arvectum.embeddings`, `127.0.0.1:8090`, `Qwen3-Embedding-4B`, 2560-dimensional live request verified.
- Docker PostgreSQL and both Arvectum launchd services survived restart smoke.
- Focused runtime tests: PASS; auth/embedding/database smoke passed after canonical restart.
- Overall closure: `R0_CODE_AND_RUNTIME_COMPLETE_PRODUCTION_PUBLICATION_PENDING`.
