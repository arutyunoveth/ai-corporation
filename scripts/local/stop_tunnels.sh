#!/usr/bin/env zsh
set -euo pipefail

RUNTIME_DIR="$HOME/arvectum-runtime"

echo "Stopping tunnels..."

# CloudPub
if [[ -f "$RUNTIME_DIR/cloudpub.pid" ]]; then
    PID=$(cat "$RUNTIME_DIR/cloudpub.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null && echo "  Stopped CloudPub (PID $PID)" || true
    fi
    rm -f "$RUNTIME_DIR/cloudpub.pid"
fi

# ngrok
if [[ -f "$RUNTIME_DIR/ngrok.pid" ]]; then
    PID=$(cat "$RUNTIME_DIR/ngrok.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null && echo "  Stopped ngrok (PID $PID)" || true
    fi
    rm -f "$RUNTIME_DIR/ngrok.pid"
fi

# cloudflared
if [[ -f "$RUNTIME_DIR/cloudflared.pid" ]]; then
    PID=$(cat "$RUNTIME_DIR/cloudflared.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null && echo "  Stopped cloudflared (PID $PID)" || true
    fi
    rm -f "$RUNTIME_DIR/cloudflared.pid"
fi

# xtunnel
if [[ -f "$RUNTIME_DIR/xtunnel.pid" ]]; then
    PID=$(cat "$RUNTIME_DIR/xtunnel.pid")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID" 2>/dev/null && echo "  Stopped xtunnel (PID $PID)" || true
    fi
    rm -f "$RUNTIME_DIR/xtunnel.pid"
fi

# CloudPub system service
if sudo clo service status > /dev/null 2>&1; then
    sudo clo service stop > /dev/null 2>&1 && echo "  Stopped CloudPub service" || true
fi

# Fallback: pkill remaining processes
pkill -f "clo" 2>/dev/null && echo "  Fallback: stopped clo" || true
pkill -f "cloudflared tunnel" 2>/dev/null && echo "  Fallback: stopped cloudflared" || true
pkill -f "ngrok http" 2>/dev/null && echo "  Fallback: stopped ngrok" || true
pkill -f xtunnel 2>/dev/null && echo "  Fallback: stopped xtunnel" || true

echo "Done."
echo "Note: backend, llama.cpp, system proxy, and PAC were NOT touched."
