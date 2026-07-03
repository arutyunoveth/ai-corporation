#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# start_llamacpp_server.sh
# Start llama.cpp server for AI-Corporation Mac mini pilot
# Listens ONLY on 127.0.0.1:8088 — NOT exposed to network
# =============================================================================

SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$HOME/arvectum-runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_FILE="$RUNTIME_DIR/llama-server.pid"

source "${PROJECT_ROOT}/.env.macmini.local" 2>/dev/null || true

LLAMA_SERVER_BIN="${LLAMA_SERVER_BIN:-/opt/homebrew/bin/llama-server}"
LLAMA_MODEL_PATH="${LLAMA_MODEL_PATH:-}"
LLAMA_PORT="${LLAMA_PORT:-8088}"
LLAMA_CTX="${LLAMA_CTX:-4096}"
LLAMA_NGL="${LLAMA_NGL:-99}"

if [[ -z "$LLAMA_MODEL_PATH" ]]; then
    echo "ERROR: LLAMA_MODEL_PATH not set. Edit scripts/local/start_llamacpp_server.sh or export it."
    echo "Example:"
    echo "  export LLAMA_MODEL_PATH=\"/Users/master/models/your-model.gguf\""
    exit 1
fi

if [[ ! -f "$LLAMA_SERVER_BIN" ]]; then
    echo "ERROR: llama-server binary not found at $LLAMA_SERVER_BIN"
    echo "Install with: brew install llama.cpp"
    exit 1
fi

if [[ ! -f "$LLAMA_MODEL_PATH" ]]; then
    echo "ERROR: Model file not found at $LLAMA_MODEL_PATH"
    exit 1
fi

mkdir -p "$LOG_DIR" "$RUNTIME_DIR"

echo "Starting llama.cpp server..."
echo "  Binary: $LLAMA_SERVER_BIN"
echo "  Model:  $LLAMA_MODEL_PATH"
echo "  Listen: 127.0.0.1:$LLAMA_PORT"
echo "  Log:    $LOG_DIR/llama-server.log"

nohup "$LLAMA_SERVER_BIN" \
    -m "$LLAMA_MODEL_PATH" \
    --host 127.0.0.1 \
    --port "$LLAMA_PORT" \
    -c "$LLAMA_CTX" \
    -ngl "$LLAMA_NGL" \
    > "$LOG_DIR/llama-server.log" 2>&1 &

echo $! > "$PID_FILE"
echo "PID: $(cat "$PID_FILE")"

sleep 5
if curl -sf http://127.0.0.1:$LLAMA_PORT/v1/models > /dev/null 2>&1; then
    echo "SUCCESS: llama.cpp server is running at http://127.0.0.1:$LLAMA_PORT"
else
    echo "WARNING: Server started but not yet responding. Check logs:"
    echo "  tail -50 $LOG_DIR/llama-server.log"
fi
