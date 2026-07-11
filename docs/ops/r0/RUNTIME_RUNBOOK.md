# Runtime runbook

```text
TLS ingress (one, approved) -> 127.0.0.1:8001 backend -> PostgreSQL 127.0.0.1:55432
                                          -> local LLM 127.0.0.1:8088
                                          -> embeddings 127.0.0.1:8090
```

## First start

```bash
cp .env.runtime.example .env.local
chmod 600 .env.local
docker compose -f docker-compose.postgres.yml up -d
python -m src.shared.runtime.preflight
./scripts/runtime/install_launchd.sh
./scripts/runtime/smoke.sh
```

Use `./scripts/runtime/status.sh` for ports and `~/Library/Logs/Arvectum/` for launchd logs. For migration work, run `alembic upgrade head` only after a verified DB backup. Restore and backup procedures are in `BACKUP_RESTORE_RUNBOOK.md`. One ingress must terminate TLS and must not expose PostgreSQL, LLM, or embeddings directly.

## Incident and release

Disable ingress first, retain logs and backup, diagnose with preflight, and restore only to a new recovery database. Release from a clean tag/checkout, run `make ci`, runtime smoke, and backup verification before switching ingress.
