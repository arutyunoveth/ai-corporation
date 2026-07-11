#!/usr/bin/env bash
set -euo pipefail
target="$HOME/Library/LaunchAgents/com.arvectum.backend.plist"
launchctl bootout "gui/$(id -u)" "$target" 2>/dev/null || true
echo "uninstalled backend launchd job; plist retained for inspection"
