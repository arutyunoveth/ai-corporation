#!/usr/bin/env bash
set -euo pipefail
base=http://127.0.0.1:18081
test "$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' "$base/health/tender-agent")" = 200
test "$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' "$base/pilot/tender-agent")" = 401
test "$(curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --user "${AI_CORP_PILOT_AUTH_USERNAME:?}:${AI_CORP_PILOT_AUTH_PASSWORD:?}" "$base/pilot/tender-agent")" = 200
echo "pilot proxy auth smoke: passed"
