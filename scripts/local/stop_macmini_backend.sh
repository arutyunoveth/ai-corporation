#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# stop_macmini_backend.sh
# Stop AI-Corporation backend container and optionally cloudflared/llama.cpp
# =============================================================================

SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$HOME/arvectum-runtime"

CONTAINER_NAME="${CONTAINER_NAME:-arvectum-pilot}"

stop_component() {
    local name="$1"
    local pid_file="$RUNTIME_DIR/${name}.pid"
    if [[ -f "$pid_file" ]]; then
        local pid
        pid=$(cat "$pid_file")
        if kill "$pid" 2>/dev/null; then
            echo "Stopped $name (PID $pid)"
        fi
        rm -f "$pid_file"
    fi
}

echo "=== Stopping backend container ==="
docker rm -f "$CONTAINER_NAME" 2>/dev/null && echo "Container $CONTAINER_NAME removed" || echo "No container $CONTAINER_NAME running"

echo ""
echo "=== Optional components ==="
echo "Stop cloudflared tunnel? (y/n)"
read -r answer
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    stop_component "cloudflared"
fi

echo "Stop llama.cpp server? (y/n)"
read -r answer
if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
    stop_component "llama-server"
fi

echo ""
echo "Done."
