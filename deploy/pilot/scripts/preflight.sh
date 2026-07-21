#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
test "$(git -C "$root" rev-parse HEAD)" = c0e7c7dbfb65765e5a918318d784115b00b4ce06
git -C "$root" diff --quiet; git -C "$root" diff --cached --quiet
test -r "${PILOT_SECRET_ENV:?}" && test "$(stat -f %Lp "$PILOT_SECRET_ENV")" = 600
test -r "${PILOT_TLS_POLICY:?}"
docker compose -f "$root/deploy/pilot/compose.yaml" config --quiet
docker info >/dev/null
echo "pilot preflight: passed"
