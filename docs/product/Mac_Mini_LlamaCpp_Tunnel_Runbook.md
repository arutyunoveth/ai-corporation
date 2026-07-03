# Mac Mini Pilot — LlamaCpp + Tunnel Runbook

## Overview

This runbook describes the **demo/pilot** deployment of the AI-Corporation backend on a local Mac mini.

### Architecture

```
arvectum.com (hosting)
    |
    v  (HTTPS)
Cloudflare Tunnel (trycloudflare.com)
    |
    v  (localhost)
Mac mini -> Docker (FastAPI backend on port 8001)
    |
    v  (host.docker.internal:8088)
llama.cpp server (127.0.0.1:8088, NOT exposed)
    |
    v  (Metal GPU)
Qwen2.5-14B-Instruct GGUF (local model)
```

- All data stays local -- no external LLM API calls
- llama.cpp listens ONLY on `127.0.0.1` -- never exposed to network
- Tunnel exposes only the FastAPI backend

## Prerequisites

- Mac mini with macOS, Docker (colima), Homebrew
- llama.cpp installed (`brew install llama.cpp`)
- GGUF model file downloaded
- cloudflared installed (`brew install cloudflared`) for tunnel

## Step 1: Find llama.cpp and model

```bash
# Find llama-server binary
which llama-server
# or
find /opt/homebrew -name "llama-server" -type f

# Find GGUF models
find ~/ -name "*.gguf" -type f
```

Set variables:
```bash
export LLAMA_SERVER_BIN="/opt/homebrew/bin/llama-server"
export LLAMA_MODEL_PATH="/Users/master/models/your-model.gguf"
```

## Step 2: Start llama.cpp server

```bash
scripts/local/start_llamacpp_server.sh
```

Or manually:
```bash
mkdir -p ~/arvectum-runtime/logs

nohup "$LLAMA_SERVER_BIN" \
    -m "$LLAMA_MODEL_PATH" \
    --host 127.0.0.1 \
    --port 8088 \
    -c 4096 \
    -ngl 99 \
    > ~/arvectum-runtime/logs/llama-server.log 2>&1 &
```

Verify:
```bash
curl http://127.0.0.1:8088/v1/models
curl http://127.0.0.1:8088/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"local-model","messages":[{"role":"user","content":"Say OK"}],"temperature":0.1}'
```

## Step 3: Start backend Docker

Build image:
```bash
docker build -t arvectum-pilot:macmini .
```

Create `.env.macmini.local` from `.env.macmini.example` and fill in secrets:
```bash
cp .env.macmini.example .env.macmini.local
# Edit password: AI_CORP_TENDER_PILOT_BASIC_AUTH_PASSWORD
```

Start container:
```bash
scripts/local/start_macmini_backend.sh
```

Or manually:
```bash
docker run -d \
    --name arvectum-pilot \
    --restart unless-stopped \
    --env-file .env.macmini.local \
    -v /Users/master/Documents/AI-Corporation/data:/app/data \
    -p 127.0.0.1:8001:8000 \
    arvectum-pilot:macmini
```

## Step 4 (Alternative — Recommended): Host uvicorn backend (no Docker)

**Why host mode is recommended for quick tunnel:**
- Docker/Colima adds a VM networking layer that can cause tunnel instability (`rpc: connection closed`)
- Host uvicorn runs directly on macOS — fewer network hops for cloudflared
- Docker/Colima mode remains available as an alternative

### 4.1: Prepare Python venv

```bash
python3 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -e .
```

### 4.2: Create host env file

```bash
cp .env.macmini.example .env.macmini.host.local
# Edit password: AI_CORP_TENDER_PILOT_BASIC_AUTH_PASSWORD
# IMPORTANT: AI_CORP_OPENAI_BASE_URL must be http://127.0.0.1:8088/v1
# (NOT host.docker.internal — that's only for Docker mode)
```

### 4.3: Start host backend

```bash
scripts/local/start_macmini_backend_host.sh
```

### 4.4: Verify backend calls llama.cpp directly

```bash
source .env.macmini.host.local
curl -s "$AI_CORP_OPENAI_BASE_URL/chat/completions" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $AI_CORP_OPENAI_API_KEY" \
    -d '{"model":"local-model","messages":[{"role":"user","content":"Say OK"}],"temperature":0.1}' | head -c 1000
```

### 4.5: Stop host backend

```bash
scripts/local/stop_macmini_backend_host.sh
```

### Env file summary

| Mode | Env file | LLM base URL |
|------|----------|-------------|
| Host (recommended) | `.env.macmini.host.local` | `http://127.0.0.1:8088/v1` |
| Docker/Colima | `.env.macmini.local` | `http://host.docker.internal:8088/v1` |

## Step 5: Verify backend to llama.cpp (Docker mode only)

```bash
docker exec arvectum-pilot python3 -c "
import json, urllib.request
url = 'http://host.docker.internal:8088/v1/chat/completions'
payload = json.dumps({'model':'local-model','messages':[{'role':'user','content':'Say OK'}],'temperature':0.1,'max_tokens':10}).encode()
req = urllib.request.Request(url, data=payload, headers={'Content-Type':'application/json','Authorization':'Bearer llama-cpp-local'})
with urllib.request.urlopen(req, timeout=30) as r:
    print(json.loads(r.read())['choices'][0]['message']['content'])
"
```

## Step 6: Start tunnel (temporary URL)

```bash
scripts/local/start_cloudflared_quick_tunnel.sh
```

This produces a URL like `https://random-words.trycloudflare.com`.

## Step 7: Update landing page

In the landing page configuration, set the backend base URL to the tunnel URL:

```javascript
window.ARVECTUM_PILOT_API_BASE = "https://random-words.trycloudflare.com";
```

## Step 8: Stop everything

### Stop host mode:
```bash
scripts/local/stop_macmini_backend_host.sh
```

### Stop Docker mode:
```bash
scripts/local/stop_macmini_backend.sh
```

### Stop tunnel and llama.cpp:
```bash
kill $(cat ~/arvectum-runtime/cloudflared.pid)       # if running
kill $(cat ~/arvectum-runtime/llama-server.pid)       # if running
```

## Health check

```bash
scripts/local/check_macmini_backend.sh
```

## Troubleshooting

### Docker doesn't see host.docker.internal

Use `docker.for.mac.host.internal` instead:
```bash
AI_CORP_OPENAI_BASE_URL=http://docker.for.mac.host.internal:8088/v1
```
Then recreate the container.

### llama.cpp not responding to /v1/chat/completions

Check the server is running with correct flags:
```bash
curl http://127.0.0.1:8088/v1/models   # should return JSON
```
If the model doesn't support chat format, try a different model or adjust template.

### CORS errors

Update `AI_CORP_CORS_ALLOW_ORIGINS` in `.env.macmini.local`:
```bash
AI_CORP_CORS_ALLOW_ORIGINS=https://arvectum.com,https://www.arvectum.com,https://*.trycloudflare.com
```

### Basic auth

All requests to `/v3/*` endpoints require basic auth:
```bash
curl -u demo:<PASSWORD> http://127.0.0.1:8001/v3/workspaces
```

### Model timeout

If LLM requests time out:
1. Check llama.cpp logs: `tail -50 ~/arvectum-runtime/logs/llama-server.log`
2. Increase `AI_CORP_LLM_TIMEOUT_SECONDS` in env file
3. Reduce context size (`-c 2048`)

### JSON response not valid

Some local models produce invalid JSON. Check response in llama.cpp logs. Try a different model or adjust temperature.

### Mac mini rebooted

After reboot:

**Recommended (host mode):**
```bash
# Start llama.cpp
scripts/local/start_llamacpp_server.sh

# Start backend (host uvicorn)
scripts/local/start_macmini_backend_host.sh

# Start tunnel
scripts/local/start_cloudflared_quick_tunnel.sh
```

**Alternative (Docker mode):**
```bash
# Start Docker (colima)
colima start

# Start llama.cpp
scripts/local/start_llamacpp_server.sh

# Start backend (Docker)
scripts/local/start_macmini_backend.sh

# Start tunnel
scripts/local/start_cloudflared_quick_tunnel.sh
```

### Proxy / PAC configuration

The Mac mini uses a system PAC (Proxy Auto-Config) for HTTP/HTTPS traffic routing:

- PAC URL: `http://127.0.0.1:8082/proxy.pac`
- Served by `tunnel-proxy.py` (launch agent `com.user.tunnel-proxy`)
- Local addresses and private networks are configured as DIRECT via both PAC and system bypass list

**What NOT to do:**
- Do NOT disable the system proxy entirely — Telegram, Hermes, GitHub depend on it
- Do NOT change llama.cpp `--host` to `0.0.0.0`
- Do NOT open backend ports on `0.0.0.0`

**How the bypass is configured:**

1. **PAC file** (`/Users/master/proxy.pac`) has DIRECT rules for:
   - `localhost`, `127.0.0.1`, `::1`, `*.local`
   - `host.docker.internal`, `docker.for.mac.host.internal`
   - Private IP ranges (`192.168.*`, `10.*`, `172.16.*` … `172.31.*`)
   - `*.trycloudflare.com`, `*.ngrok-free.app`, `*.ngrok.io`, `ngrok.com`

2. **System bypass list** (macOS network settings) mirrors the PAC rules.

3. **Cloudflared** is launched with proxy env vars cleared (`ARVECTUM_TUNNEL_BYPASS_PROXY=true`),
   so it connects to Cloudflare edge directly, not through the proxy.

**To verify proxy status:**
```bash
scutil --proxy

# Check PAC is enabled
networksetup -getautoproxyurl Wi-Fi

# Check bypass domains
networksetup -getproxybypassdomains Wi-Fi

# Verify PAC content
curl --noproxy "*" -s http://127.0.0.1:8082/proxy.pac | head -40
```

**To test local services bypass the proxy:**
```bash
curl --noproxy "*" -s http://127.0.0.1:8088/v1/models
curl --noproxy "*" -I http://127.0.0.1:8001/
```

**If Telegram / Hermes stop working after proxy changes:**
- Check `launchctl list | grep tunnel-proxy` — must be running
- Check `scutil --proxy` — PAC must be enabled, `HTTPEnable` should be 0
- If tunnel-proxy was unloaded: `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.user.tunnel-proxy.plist`

**To add new domains to PAC DIRECT list:**
Edit `/Users/master/proxy.pac` and add entries to the `direct` array, then the tunnel-proxy
will serve the updated PAC automatically.

### Tunnel URL changed

Quick tunnel URLs are temporary. After restart, get the new URL:
```bash
grep -Eo "https://[-a-zA-Z0-9.]+trycloudflare.com" ~/arvectum-runtime/logs/cloudflared.log | tail -1
```
Update the landing page with the new URL.

## Known Limitations

- Tunnel URL is **temporary** -- changes on each cloudflared restart
- Mac mini must stay powered on and awake
- llama.cpp listens on **127.0.0.1 only** -- DO NOT change to 0.0.0.0
- Local model quality should be compared with GigaChat/YandexGPT
- This is a **demo/pilot** setup, not production-ready
