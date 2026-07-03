#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# start_cloudflared_quick_tunnel.sh
# Start Cloudflare quick tunnel for Mac mini pilot
# 
# WARNING: The tunnel URL is TEMPORARY and changes on each restart.
# For a permanent URL, configure a named tunnel with cloudflared tunnel create.
# =============================================================================

SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$HOME/arvectum-runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_FILE="$RUNTIME_DIR/cloudflared.pid"

BACKEND_PORT="${BACKEND_PORT:-8001}"

mkdir -p "$LOG_DIR" "$RUNTIME_DIR"

# Check cloudflared
if ! command -v cloudflared &>/dev/null; then
    echo "ERROR: cloudflared not found. Install with: brew install cloudflared"
    exit 1
fi

echo "Starting cloudflared quick tunnel..."
echo "  Backend URL: http://127.0.0.1:${BACKEND_PORT}"
echo "  Log file:    $LOG_DIR/cloudflared.log"
echo ""

nohup cloudflared tunnel --url "http://127.0.0.1:${BACKEND_PORT}" --protocol http2 \
    > "$LOG_DIR/cloudflared.log" 2>&1 &

echo $! > "$PID_FILE"
echo "PID: $(cat "$PID_FILE")"

echo ""
echo "Waiting for tunnel URL..."
for i in $(seq 1 15); do
    TUNNEL_URL=$(grep -Eo "https://[-a-zA-Z0-9.]+trycloudflare.com" "$LOG_DIR/cloudflared.log" 2>/dev/null | tail -1)
    if [[ -n "$TUNNEL_URL" ]]; then
        echo ""
        echo "SUCCESS: Tunnel is live!"
        echo "  Tunnel URL: $TUNNEL_URL"
        echo ""
        echo "Add this to your landing page backend base URL."
        echo "NOTE: This URL changes every time cloudflared restarts."
        exit 0
    fi
    sleep 1
done

echo ""
echo "WARNING: Tunnel URL not yet available. Check logs:"
echo "  tail -50 $LOG_DIR/cloudflared.log"
