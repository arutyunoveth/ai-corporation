#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)
env_file=${ARVECTUM_ENV_FILE:-"$root/.env.local"}
[[ -f "$env_file" ]] || { echo "missing $env_file" >&2; exit 2; }
set -a; source "$env_file"; set +a
python_bin=${ARVECTUM_PYTHON:-"$root/.venv/bin/python"}
exec "$python_bin" -m uvicorn src.main:app --host 127.0.0.1 --port "${AI_CORP_BACKEND_PORT:-8001}"
