#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# start_cloudflared_quick_tunnel.sh
# Start Cloudflare quick tunnel for Mac mini pilot.
#
# Tunnels to ARVECTUM_TUNNEL_TARGET (default http://127.0.0.1:8001).
# Set ARVECTUM_TUNNEL_TARGET to change target (e.g. for Docker mode).
#
# WARNING: The tunnel URL is TEMPORARY and changes on each restart.
# For a permanent URL, configure a named tunnel with cloudflared tunnel create.
# =============================================================================

SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$HOME/arvectum-runtime"
LOG_DIR="$RUNTIME_DIR/logs"
PID_FILE="$RUNTIME_DIR/cloudflared.pid"

ARVECTUM_TUNNEL_TARGET="${ARVECTUM_TUNNEL_TARGET:-http://127.0.0.1:8001}"

mkdir -p "$LOG_DIR" "$RUNTIME_DIR"

# Check cloudflared
if ! command -v cloudflared &>/dev/null; then
    echo "ERROR: cloudflared not found. Install with: brew install cloudflared"
    exit 1
fi

echo "Starting cloudflared quick tunnel..."
echo "  Target URL: $ARVECTUM_TUNNEL_TARGET"
echo "  Log file:   $LOG_DIR/cloudflared.log"
echo ""

nohup cloudflared tunnel --url "$ARVECTUM_TUNNEL_TARGET" --protocol http2 \
    > "$LOG_DIR/cloudflared.log" 2>&1 &

echo $! > "$PID_FILE"
echo "PID: $(cat "$PID_FILE")"

echo ""
echo "Waiting for tunnel URL..."
for i in $(seq 1 20); do
    TUNNEL_URL=$(grep -Eo "https://[-a-zA-Z0-9.]+trycloudflare.com" "$LOG_DIR/cloudflared.log" 2>/dev/null | tail -1)
    if [[ -n "$TUNNEL_URL" ]]; then
        echo ""
        echo "=============================================="
        echo "  Tunnel is LIVE!"
        echo "  Tunnel URL: $TUNNEL_URL"
        echo "=============================================="
        echo ""
        echo "Add this to your landing page backend base URL:"
        echo "  window.ARVECTUM_PILOT_API_BASE = \"$TUNNEL_URL\";"
        echo ""
        echo "IMPORTANT: This URL is TEMPORARY."
        echo "It changes every time cloudflared restarts."
        echo "For persistent tunnel, use: cloudflared tunnel create"
        exit 0
    fi
    sleep 1
done

echo ""
echo "WARNING: Tunnel URL not yet available. Check logs:"
echo "  tail -50 $LOG_DIR/cloudflared.log"
echo ""
echo "The system HTTPS proxy may be interfering. Check:"
echo "  networksetup -getsecurewebproxy Wi-Fi"
