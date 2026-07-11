# R0.01 preflight inventory

Generated: 2026-07-11 UTC. This is a factual snapshot taken before R0 changes.

## Checkout discovery

| Checkout | HEAD | Branch | State | Role |
|---|---|---|---|---|
| `/Users/master/Documents/AI-Corporation` | `1fdb853` | `main` (behind `origin/main` by 51) | dirty, tracked and untracked recovery work | developer checkout; not runtime source of truth |
| `/Users/master/Documents/AI-Corporation-live` | `71c2fea` | `feat/eis-production-ingestion-triage` | dirty, ahead 1 | existing runtime candidate; preserved, not overwritten |
| `AI-Corporation-live-smoke-8aa1d0c6` | `758ed3b` | `merge/main-integration` | clean | historical smoke worktree |
| `AI-Corporation-merge-demo-export` | `e6bf33c` | `merge/demo-agent-export` | clean | historical merge worktree |
| `AI-Corporation-merge-docs-demo` | `54d28b8` | `merge/docs-final-demo` | clean | historical merge worktree |
| `AI-Corporation-merge-report-export` | `8eec855` | `merge/report-export-main` | clean | historical merge worktree |
| `/Users/master/Documents/AI-Corporation-r0` | `8998ddb` | `codex/r0-sync-2026-07-11` | clean at creation | R0 integration checkout |

`arvectum-landing` had no local Git checkout at discovery time. A clean checkout from `origin/main` is created only for R0 integration; the repository is independently backed up by GitHub until it contains local work.

## Runtime snapshot

| Component | Observed state |
|---|---|
| Backend | unrelated local service on `127.0.0.1:8000`; no service on `8001` |
| PostgreSQL | Homebrew PostgreSQL 18 on `127.0.0.1:5432`; `55432` was not listening |
| Chat LLM | local server listening on `8088` (not yet proven to be Arvectum-compatible) |
| Embeddings | no listener on `8090` |
| Docker | daemon available; no running containers |
| launchd | Homebrew PostgreSQL, Ollama, and a `local.llama-server` job found; no Arvectum launchd jobs found |

Runtime directories were found under both developer and live checkout. They are archived as data, not committed.

## Masked configuration and data handling

Existing `.env*` files were copied only to a `0600` archive outside Git. The backup contains inventories of variable names and `SET` markers; neither this document nor any committed artifact contains their values.

## Backup result

- Directory: `/Users/master/Documents/arvectum-r0-backups/20260711-145008`
- Git bundle: verified; 52 refs
- Runtime data archive: verified; 1,940 entries
- PostgreSQL dumps: `ai_corporation` and `tender_db`, both verified with `pg_restore --list`
- Backup size at verification: approximately 55 MiB

See `BACKUP_RESTORE_RUNBOOK.md` for verification and restore procedures.
