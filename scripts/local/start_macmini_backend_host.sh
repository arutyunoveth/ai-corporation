#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# start_macmini_backend_host.sh
# Start AI-Corporation backend DIRECTLY on macOS (no Docker).
# Listens ONLY on 127.0.0.1 — NOT exposed to network.
# Recommended mode for stable cloudflared quick tunnel.
# =============================================================================

SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$HOME/arvectum-runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_FILE="$RUNTIME_DIR/backend-host.pid"
ENV_FILE="${PROJECT_ROOT}/.env.macmini.host.local"
VENV_PYTHON="${PROJECT_ROOT}/.venv/bin/python"
BACKEND_PORT="${BACKEND_PORT:-8001}"

mkdir -p "$LOG_DIR" "$RUNTIME_DIR" "${PROJECT_ROOT}/data"

if [[ ! -f "$VENV_PYTHON" ]]; then
    echo "ERROR: .venv not found at $VENV_PYTHON"
    echo "Run: cd $PROJECT_ROOT && python3 -m venv .venv && .venv/bin/pip install -e ."
    exit 1
fi

if [[ ! -f "$ENV_FILE" ]]; then
    echo "ERROR: Env file not found at $ENV_FILE"
    echo "Copy .env.macmini.example or create .env.macmini.host.local"
    exit 1
fi

echo "Starting backend (host mode)..."
echo "  Python:  $VENV_PYTHON"
echo "  Env:     $ENV_FILE"
echo "  Listen:  127.0.0.1:$BACKEND_PORT"
echo "  Log:     $LOG_DIR/backend-host.log"
echo "  PID:     $PID_FILE"

export $(grep -v "^\s*#" "$ENV_FILE" | grep -v "^\s*$" | xargs)

nohup "$VENV_PYTHON" -m uvicorn src.main:app \
    --host 127.0.0.1 \
    --port "$BACKEND_PORT" \
    --proxy-headers \
    > "$LOG_DIR/backend-host.log" 2>&1 &

echo $! > "$PID_FILE"
echo "PID: $(cat "$PID_FILE")"

sleep 3
if curl -sf "http://127.0.0.1:${BACKEND_PORT}/" > /dev/null 2>&1; then
    echo "SUCCESS: Backend running at http://127.0.0.1:${BACKEND_PORT}"
    echo "LLM endpoint: http://127.0.0.1:8088/v1"
else
    echo "WARNING: Backend started but not yet responding. Check logs:"
    echo "  tail -30 $LOG_DIR/backend-host.log"
fi
