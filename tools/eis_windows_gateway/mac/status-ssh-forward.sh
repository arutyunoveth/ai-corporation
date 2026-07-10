#!/usr/bin/env bash
set -euo pipefail

local_port="${1:-18110}"
lsof -nP -iTCP:"$local_port" -sTCP:LISTEN
