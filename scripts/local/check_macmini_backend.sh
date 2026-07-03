#!/usr/bin/env zsh
set -euo pipefail

# =============================================================================
# check_macmini_backend.sh
# Health check for Mac mini pilot deployment (host + Docker modes)
# =============================================================================

BACKEND_PORT="${BACKEND_PORT:-8001}"
LLAMA_PORT="${LLAMA_PORT:-8088}"
CONTAINER_NAME="${CONTAINER_NAME:-arvectum-pilot}"
RUNTIME_DIR="$HOME/arvectum-runtime"
ENV_FILE_HOST="${ENV_FILE_HOST:-$HOME/Documents/AI-Corporation/.env.macmini.host.local}"

echo "================================================"
echo "  Mac mini Pilot — Health Check"
echo "================================================"

echo ""
echo "=== 1. llama.cpp server ==="
if curl -sf "http://127.0.0.1:${LLAMA_PORT}/v1/models" > /dev/null 2>&1; then
    echo "OK: llama.cpp responding at http://127.0.0.1:${LLAMA_PORT}"
    curl -s "http://127.0.0.1:${LLAMA_PORT}/v1/models" | python3 -c "import sys,json;d=json.load(sys.stdin);[print(f'  - {m[\"model\"]}') for m in d.get('data',[])]" 2>/dev/null || true
else
    echo "WARNING: llama.cpp not responding"
fi

echo ""
echo "=== 2. Host backend (127.0.0.1:$BACKEND_PORT) ==="
if curl -sf "http://127.0.0.1:${BACKEND_PORT}/pilot/tender-agent" > /dev/null 2>&1; then
    echo "  Endpoint /pilot/tender-agent: responding"
elif curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:${BACKEND_PORT}/pilot/tender-agent" 2>/dev/null | grep -q "401\|404"; then
    echo "  Endpoint /pilot/tender-agent: reachable (needs auth)"
else
    echo "WARNING: Host backend not responding"
fi

echo ""
echo "=== 3. Host backend — basic auth endpoint ==="
if [[ -f "$ENV_FILE_HOST" ]]; then
    source "$ENV_FILE_HOST"
    PASSWORD="${AI_CORP_TENDER_PILOT_BASIC_AUTH_PASSWORD:-}"
    if [[ -n "$PASSWORD" ]]; then
        HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "demo:$PASSWORD" "http://127.0.0.1:${BACKEND_PORT}/pilot/tender-agent" 2>/dev/null || echo "failed")
        echo "  /pilot/tender-agent with auth: HTTP $HTTP_CODE"
    else
        echo "  PASSWORD not found in $ENV_FILE_HOST"
    fi
else
    echo "  No $ENV_FILE_HOST — skipping auth check"
fi

echo ""
echo "=== 4. OpenAI-compatible LLM via host env ==="
if [[ -f "$ENV_FILE_HOST" ]]; then
    source "$ENV_FILE_HOST"
    LLM_URL="${AI_CORP_OPENAI_BASE_URL:-http://127.0.0.1:8088/v1}"
    LLM_KEY="${AI_CORP_OPENAI_API_KEY:-llama-cpp-local}"
    echo "  Testing $LLM_URL/chat/completions ..."
    curl -s "$LLM_URL/chat/completions" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $LLM_KEY" \
        -d '{"model":"local-model","messages":[{"role":"user","content":"OK"}],"temperature":0.1,"max_tokens":10}' 2>/dev/null | \
        python3 -c "import sys,json;d=json.load(sys.stdin);print(f'  Response: {d[\"choices\"][0][\"message\"][\"content\"][:50]}')" 2>/dev/null || echo "  LLM call failed"
fi

echo ""
echo "=== 5. Docker container (optional) ==="
if command -v docker &>/dev/null; then
    if docker ps --filter "name=$CONTAINER_NAME" --format "{{.ID}} {{.Status}} {{.Ports}}" 2>/dev/null | grep -q "$CONTAINER_NAME"; then
        docker ps --filter "name=$CONTAINER_NAME" --format "table {{.ID}}\t{{.Status}}\t{{.Ports}}"
    else
        echo "  Container $CONTAINER_NAME not running (optional)"
    fi
else
    echo "  Docker not available"
fi

echo ""
echo "=== 6. CloudPub tunnel ==="
CLOUDPUB_URL=""
if command -v clo &>/dev/null; then
    if sudo clo service status > /dev/null 2>&1; then
        CLOUDPUB_URL=$(clo ls 2>/dev/null | grep -Eo "https://[^ ]+" | head -1)
        if [[ -n "$CLOUDPUB_URL" ]]; then
            echo "  CloudPub service running"
            echo "  URL: $CLOUDPUB_URL"
            if [[ -f "$ENV_FILE_HOST" ]]; then
                source "$ENV_FILE_HOST"
                HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" -u "demo:${AI_CORP_TENDER_PILOT_BASIC_AUTH_PASSWORD}" "$CLOUDPUB_URL/pilot/tender-agent" 2>/dev/null || echo "failed")
                echo "  Tunnel /pilot/tender-agent: HTTP $HTTP_CODE"
            fi
            echo ""
            echo "  >>> Landing page config:"
            echo "  window.ARVECTUM_PILOT_API_BASE = \"$CLOUDPUB_URL\";"
        else
            echo "  CloudPub service running but URL not found"
        fi
    else
        echo "  CloudPub not available (service not installed or stopped)"
    fi
else
    echo "  CloudPub CLI not installed"
fi

echo ""
echo "=== 7. Cloudflared (legacy) ==="
if [[ -f "$RUNTIME_DIR/cloudflared.pid" ]]; then
    CFD_PID=$(cat "$RUNTIME_DIR/cloudflared.pid")
    if kill -0 "$CFD_PID" 2>/dev/null; then
        CFD_URL=$(grep -Eo "https://[-a-zA-Z0-9.]+trycloudflare.com" "$RUNTIME_DIR/logs/cloudflared.log" 2>/dev/null | tail -1)
        echo "  Cloudflared running: ${CFD_URL:-URL not found}"
    else
        echo "  Cloudflared PID $CFD_PID not running (stale PID)"
    fi
else
    echo "  Cloudflared not running"
fi

echo ""
echo "=== 8. Runtime PID files ==="
ls -la "$RUNTIME_DIR"/*.pid 2>/dev/null || echo "  No PID files found"

echo ""
echo "================================================"
echo "  Check complete"
echo "================================================"
