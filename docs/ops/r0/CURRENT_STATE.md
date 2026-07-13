# Current state

Generated 2026-07-13 UTC from final acceptance records.

- Product functional main: `2578d114074685ddb072736839b6023897105bcd`; release tag `r0-sync-2026-07-11` remains unchanged.
- Site production main: `9b87212500b48ec918973f0e38351a5ad14b2603`.
- Migration head: `092_create_tender_analysis_jobs_table`.
- PostgreSQL: Docker `pgvector/pgvector:pg17` on host `127.0.0.1:55432`, pgvector `0.8.4`, Alembic head `092_create_tender_analysis_jobs_table`; Homebrew PostgreSQL 18 on `5432` preserved.
- Backend: launchd `com.arvectum.backend`, `127.0.0.1:8001`, public `/health` and protected readiness/OpenAPI verified.
- LLM: Homebrew-managed Ollama OpenAI-compatible API `127.0.0.1:11434/v1`; port `8088` is not an LLM endpoint.
- Embeddings: launchd `com.arvectum.embeddings`, `127.0.0.1:8090`, `Qwen3-Embedding-4B`, 2560-dimensional live request verified.
- Docker PostgreSQL and both Arvectum launchd services survived restart smoke.
- Focused runtime tests: PASS; auth/embedding/database smoke passed after canonical restart.
- Temporary ingress: `https://punctually-ubiquitous-aphid.cloudpub.ru`; public site: `https://arvectum.com`.
- Acceptance: live procurement, getDocsIP, analysis, exports, Chromium/WebKit, mobile, LTE/5G, cookie consent, and post-reboot autostart PASS.
- Overall closure: `R0_CLOSED_FUNCTIONALLY`; CloudPub limitation `PUBLIC_RELIABILITY_LIMITED_NOT_PROVEN`.
