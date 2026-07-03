#!/usr/bin/env zsh
set -euo pipefail

SCRIPT_DIR="${0:a:h}"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
RUNTIME_DIR="$HOME/arvectum-runtime"

ARVECTUM_TUNNEL_TARGET="${ARVECTUM_TUNNEL_TARGET:-http://127.0.0.1:8001}"
CLOUDPUB_SERVICE_NAME="${CLOUDPUB_SERVICE_NAME:-Arvectum-backend}"

mkdir -p "$RUNTIME_DIR"

if ! command -v clo &>/dev/null; then
    echo "ERROR: clo (CloudPub CLI) not found."
    echo "Install: curl -L https://cloudpub.ru/download/stable/clo-3.1.0-stable-macos-aarch64.tar.gz | tar -xz && sudo cp clo /opt/homebrew/bin/clo"
    echo "Then: clo login"
    exit 1
fi

echo "Starting CloudPub tunnel..."
echo "  Target: $ARVECTUM_TUNNEL_TARGET"
echo "  Service: $CLOUDPUB_SERVICE_NAME"
echo ""

# Register the service (idempotent)
clo register http "${ARVECTUM_TUNNEL_TARGET##*:}" --name "$CLOUDPUB_SERVICE_NAME" > /dev/null 2>&1 || true

# Check if service is installed
SERVICE_INSTALLED=false
if sudo clo service status > /dev/null 2>&1; then
    SERVICE_INSTALLED=true
fi

if [[ "$SERVICE_INSTALLED" == "false" ]]; then
    echo "Installing CloudPub as system service (sudo required)..."
    sudo clo service install > /dev/null 2>&1
fi

sudo clo service start > /dev/null 2>&1
echo "Service started."

# Get PID via launchctl
LAUNCHD_LABEL=$(sudo launchctl list | grep clo | awk '{print $3}' 2>/dev/null | head -1)
if [[ -n "$LAUNCHD_LABEL" ]]; then
    CLO_PID=$(sudo launchctl list "$LAUNCHD_LABEL" 2>/dev/null | awk '{print $1}' | head -1)
    echo "$CLO_PID" > "$RUNTIME_DIR/cloudpub.pid" 2>/dev/null || true
fi

echo ""
echo "Waiting for tunnel..."
for i in $(seq 1 15); do
    CLOUD_PUB_URL=$(clo ls 2>/dev/null | grep -Eo "https://[^ ]+" | head -1)
    if [[ -n "$CLOUD_PUB_URL" ]]; then
        echo ""
        echo "=============================================="
        echo "  Tunnel is LIVE!"
        echo "  Tunnel URL: $CLOUD_PUB_URL"
        echo "=============================================="
        echo ""
        echo "Add this to your landing page backend base URL:"
        echo "  window.ARVECTUM_PILOT_API_BASE = \"$CLOUD_PUB_URL\";"
        echo ""
        echo "NOTE: CloudPub URL is stable but may change on re-registration."
        echo "For a permanent URL, consider a paid CloudPub plan or VPS reverse proxy."
        exit 0
    fi
    sleep 2
done

echo ""
echo "WARNING: Tunnel URL not yet available. Check status:"
echo "  sudo clo service status"
echo "  clo ls"
