#!/usr/bin/env bash
set -euo pipefail

root=$(cd "$(dirname "$0")/../../.." && pwd)
compose="$root/deploy/pilot/compose.yaml"

# Keep deployment-only prerequisites detectable before an expensive staging start.
rg -q 'image: pgvector/pgvector:pg16' "$compose"
rg -q 'pilot-artifacts:/app/company_agent_runs' "$compose"
rg -q 'networks: \[pilot-internal, pilot-egress\]' "$compose"
rg -q 'pilot-internal: \{ internal: true \}' "$compose"
rg -q 'pilot-egress: \{\}' "$compose"
rg -q '127\.0\.0\.1:18081:8080' "$compose"

echo "pilot package validation: passed"
