#!/usr/bin/env bash
set -euo pipefail
"$(dirname "$0")/stop.sh"
echo "Restart through launchd after installation."
