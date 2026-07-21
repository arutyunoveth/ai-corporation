#!/usr/bin/env bash
set -euo pipefail
root=$(cd "$(dirname "$0")/../../.." && pwd)
git -C "$root" merge-base --is-ancestor c0e7c7dbfb65765e5a918318d784115b00b4ce06 HEAD
git -C "$root" diff --quiet; git -C "$root" diff --cached --quiet
test -r "${PILOT_SECRET_ENV:?}" && test "$(stat -f %Lp "$PILOT_SECRET_ENV")" = 600
test -r "${PILOT_TLS_POLICY:?}"
docker info >/dev/null
"$root/deploy/pilot/scripts/validate-package.sh"
PILOT_SECRET_ENV="$PILOT_SECRET_ENV" PILOT_TLS_POLICY="$PILOT_TLS_POLICY" docker compose --env-file "$PILOT_SECRET_ENV" -f "$root/deploy/pilot/compose.yaml" config --quiet
echo "pilot preflight: passed"
