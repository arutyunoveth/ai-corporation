#!/usr/bin/env bash
set -euo pipefail
test "${PILOT_RESTORE_CONFIRM:-}" = RESTORE_INTO_EMPTY_STAGING || { echo 'Set PILOT_RESTORE_CONFIRM=RESTORE_INTO_EMPTY_STAGING'; exit 2; }
echo "Restore only into an empty staging stack; verify alembic head and readiness afterwards."
