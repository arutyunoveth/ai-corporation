#!/usr/bin/env bash
# Verify an Arvectum backup without restoring it into any runtime database.
set -euo pipefail

backup_dir=${1:?usage: verify_backup.sh /absolute/path/to/backup}
bundle="$backup_dir/ai-corporation-all-refs.bundle"

[[ -d "$backup_dir" ]] || { echo "backup directory does not exist" >&2; exit 2; }
[[ -f "$bundle" ]] || { echo "git bundle is missing" >&2; exit 3; }
git bundle verify "$bundle"

if [[ -f "$backup_dir/runtime-data.tar.gz" ]]; then
  tar -tzf "$backup_dir/runtime-data.tar.gz" >/dev/null
fi

for dump in "$backup_dir"/*.dump; do
  [[ -f "$dump" ]] || continue
  command -v pg_restore >/dev/null || { echo "pg_restore is required for dump verification" >&2; exit 4; }
  pg_restore --list "$dump" >/dev/null
done

[[ -f "$backup_dir/backup-manifest.sha256" ]] || { echo "backup hash manifest is missing" >&2; exit 5; }
(cd "$backup_dir" && shasum -a 256 -c backup-manifest.sha256)
echo "backup verified: $backup_dir"
