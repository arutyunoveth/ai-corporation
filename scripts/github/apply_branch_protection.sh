#!/usr/bin/env bash
set -euo pipefail
repo=${1:-arutyunoveth/ai-corporation}
gh api --method PUT "repos/$repo/branches/main/protection" --input - <<'JSON'
{"required_status_checks":{"strict":false,"contexts":["quality","migrations","security"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null,"allow_force_pushes":false,"allow_deletions":false}
JSON
