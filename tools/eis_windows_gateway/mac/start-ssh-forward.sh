#!/usr/bin/env bash
set -euo pipefail

alias_name="${1:-windows}"
local_port="${2:-18110}"
remote_port="${3:-8110}"
control_path="${TMPDIR:-/tmp}/arvectum-eis-vbs-${local_port}.ctl"

ssh -M -S "$control_path" -f -N \
  -o ExitOnForwardFailure=yes \
  -o ServerAliveInterval=30 \
  -o ServerAliveCountMax=3 \
  -L "127.0.0.1:${local_port}:127.0.0.1:${remote_port}" \
  "$alias_name"

printf 'SSH forward started: 127.0.0.1:%s -> %s 127.0.0.1:%s\n' "$local_port" "$alias_name" "$remote_port"
