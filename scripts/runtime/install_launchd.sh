#!/usr/bin/env bash
set -euo pipefail
root=$(git rev-parse --show-toplevel)
target="$HOME/Library/LaunchAgents/com.arvectum.backend.plist"
mkdir -p "$(dirname "$target")" "$HOME/Library/Logs/Arvectum"
sed -e "s|__ROOT__|$root|g" -e "s|__LOG_DIR__|$HOME/Library/Logs/Arvectum|g" "$root/scripts/runtime/com.arvectum.backend.plist.template" > "$target"
plutil -lint "$target"
launchctl bootout "gui/$(id -u)" "$target" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$target"
