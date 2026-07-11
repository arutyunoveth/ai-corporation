#!/usr/bin/env bash
set -euo pipefail
base=${ARVECTUM_BACKEND_URL:-http://127.0.0.1:8001}
curl --fail --silent --show-error "$base/health" | grep -qx '{"status":"ok"}'
echo "public health: ok"
