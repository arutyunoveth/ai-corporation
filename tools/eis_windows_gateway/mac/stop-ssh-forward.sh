#!/usr/bin/env bash
set -euo pipefail

alias_name="${1:-windows}"
local_port="${2:-18110}"
control_path="${TMPDIR:-/tmp}/arvectum-eis-vbs-${local_port}.ctl"

ssh -S "$control_path" -O exit "$alias_name"
