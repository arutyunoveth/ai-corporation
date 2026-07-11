#!/usr/bin/env bash
set -euo pipefail
for target in "$HOME/Library/LaunchAgents/com.arvectum.backend.plist" "$HOME/Library/LaunchAgents/com.arvectum.embeddings.plist"; do
  launchctl bootout "gui/$(id -u)" "$target" 2>/dev/null || true
done
echo "uninstalled Arvectum launchd jobs; plists retained for inspection"
