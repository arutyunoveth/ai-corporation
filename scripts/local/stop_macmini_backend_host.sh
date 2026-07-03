#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# stop_macmini_backend_host.sh
# Stop the host-mode backend (without Docker).
# Does NOT touch Docker container or llama.cpp.
# =============================================================================

RUNTIME_DIR="$HOME/arvectum-runtime"
PID_FILE="$RUNTIME_DIR/backend-host.pid"

if [[ ! -f "$PID_FILE" ]]; then
    echo "No PID file at $PID_FILE — backend host may not be running."
    exit 0
fi

PID=$(cat "$PID_FILE")

if kill "$PID" 2>/dev/null; then
    echo "Stopped backend host (PID $PID)"
else
    echo "Process $PID not found — was it already stopped?"
fi

rm -f "$PID_FILE"
echo "PID file removed."
