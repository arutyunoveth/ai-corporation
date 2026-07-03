#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# check_macmini_backend.sh
# Health check for Mac mini pilot deployment
# =============================================================================

BACKEND_PORT="${BACKEND_PORT:-8001}"
LLAMA_PORT="${LLAMA_PORT:-8088}"
CONTAINER_NAME="${CONTAINER_NAME:-arvectum-pilot}"
RUNTIME_DIR="$HOME/arvectum-runtime"

echo "================================================"
echo "  Mac mini Pilot — Health Check"
echo "================================================"

echo ""
echo "=== 1. Docker container ==="
if docker ps --filter "name=$CONTAINER_NAME" --format "{{.ID}} {{.Status}} {{.Ports}}" 2>/dev/null | grep -q "$CONTAINER_NAME"; then
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.ID}}\t{{.Status}}\t{{.Ports}}"
else
    echo "WARNING: Container $CONTAINER_NAME not running"
fi

echo ""
echo "=== 2. llama.cpp server ==="
if curl -sf "http://127.0.0.1:${LLAMA_PORT}/v1/models" > /dev/null 2>&1; then
    echo "OK: llama.cpp responding at http://127.0.0.1:${LLAMA_PORT}"
    curl -s "http://127.0.0.1:${LLAMA_PORT}/v1/models" | python3 -m json.tool 2>/dev/null | head -5 || true
else
    echo "WARNING: llama.cpp not responding"
fi

echo ""
echo "=== 3. Backend local endpoint ==="
if curl -sf "http://127.0.0.1:${BACKEND_PORT}/" > /dev/null 2>&1; then
    echo "OK: Backend responding at http://127.0.0.1:${BACKEND_PORT}"
    curl -sI "http://127.0.0.1:${BACKEND_PORT}/" | head -3
else
    echo "WARNING: Backend not responding"
fi

echo ""
echo "=== 4. Backend to LLM connection ==="
docker exec "$CONTAINER_NAME" python3 -c "
import json, urllib.request
url = http://host.docker.internal:/v1/chat/completions
payload = json.dumps({model: local-model, messages: [{role: user, content: Say OK}], temperature: 0.1, max_tokens: 10}).encode()
req = urllib.request.Request(url, data=payload, headers={Content-Type: application/json, Authorization: Bearer llama-cpp-local})
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read())
        print(OK: Backend → llama.cpp works)
        print(Response:, data[choices][0][message][content])
except Exception as e:
    print(fERROR: {e})
" 2>&1

echo ""
echo "=== 5. Cloudflared tunnel ==="
TUNNEL_URL=""
if [[ -f "$RUNTIME_DIR/cloudflared.pid" ]]; then
    TUNNEL_URL=$(grep -Eo "https://[-a-zA-Z0-9.]+trycloudflare.com" "$RUNTIME_DIR/logs/cloudflared.log" 2>/dev/null | tail -1)
    if [[ -n "$TUNNEL_URL" ]]; then
        echo "Tunnel running: $TUNNEL_URL"
        echo "Testing tunnel..."
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$TUNNEL_URL/" 2>/dev/null || echo "failed")
        echo "Tunnel HTTP status: $HTTP_CODE"
    else
        echo "Tunnel process running but URL not found yet"
    fi
else
    echo "Cloudflared tunnel not running"
fi

echo ""
echo "=== 6. Arvectum Runtime PID files ==="
ls -la "$RUNTIME_DIR"/*.pid 2>/dev/null || echo "No PID files found"

echo ""
echo "================================================"
echo "  Check complete"
echo "================================================"
