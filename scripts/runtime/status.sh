#!/usr/bin/env bash
set -euo pipefail
for port in 55432 8001 8088 8090; do
  if nc -z 127.0.0.1 "$port" 2>/dev/null; then echo "$port: listening"; else echo "$port: unavailable"; fi
done
