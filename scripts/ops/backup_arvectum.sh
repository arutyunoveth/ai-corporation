#!/usr/bin/env bash
# Create a non-destructive, local-only Arvectum backup.  It never changes a checkout.
set -euo pipefail

repo_root=$(git rev-parse --show-toplevel)
backup_root=${ARVECTUM_BACKUP_ROOT:-"$(dirname "$repo_root")/arvectum-r0-backups"}
timestamp=$(date -u +%Y%m%d-%H%M%S)
backup_dir="$backup_root/$timestamp"
mkdir -p "$backup_dir/checkouts"
chmod 700 "$backup_root" "$backup_dir"

archive_checkout() {
  local checkout=$1 name out env_list
  name=$(basename "$checkout")
  out="$backup_dir/checkouts/$name"
  mkdir -p "$out"

  git -C "$checkout" status --short --branch > "$out/git-status.txt"
  git -C "$checkout" log --oneline --decorate -n 80 > "$out/git-log.txt"
  git -C "$checkout" branch -avv > "$out/git-branches.txt"
  git -C "$checkout" remote -v > "$out/git-remotes.txt"
  git -C "$checkout" worktree list --porcelain > "$out/git-worktrees.txt"
  git -C "$checkout" stash list > "$out/git-stash.txt"
  git -C "$checkout" diff --binary > "$out/tracked-diff.patch"
  git -C "$checkout" diff --cached --binary > "$out/staged-diff.patch"
  git -C "$checkout" ls-files --others --exclude-standard -z > "$out/untracked-files.nul"
  if [[ -s "$out/untracked-files.nul" ]]; then
    (
      cd "$checkout"
      tar --null --files-from="$out/untracked-files.nul" \
        --exclude='.env*' --exclude='.venv' --exclude='node_modules' \
        --exclude='*.gguf' --exclude='__pycache__' \
        -czf "$out/untracked-files.tar.gz"
    ) || true
  fi

  env_list="$out/env-paths.nul"
  find "$checkout" -maxdepth 2 -type f \( -name '.env' -o -name '.env.*' \) -print0 > "$env_list"
  if [[ -s "$env_list" ]]; then
    tar --null --files-from="$env_list" -czf "$out/env-files.tar.gz"
    chmod 600 "$out/env-files.tar.gz"
  fi
}

while IFS= read -r checkout; do
  archive_checkout "$checkout"
done < <(git -C "$repo_root" worktree list --porcelain | awk '/^worktree / {print substr($0, 10)}')

git -C "$repo_root" bundle create "$backup_dir/ai-corporation-all-refs.bundle" --all
git -C "$repo_root" bundle verify "$backup_dir/ai-corporation-all-refs.bundle" > "$backup_dir/bundle-verify.txt"

find "$repo_root" -maxdepth 2 -type d \( -name data -o -name company_agent_runs \) -print0 > "$backup_dir/runtime-data-paths.nul"
if [[ -s "$backup_dir/runtime-data-paths.nul" ]]; then
  tar --null --files-from="$backup_dir/runtime-data-paths.nul" \
    --exclude='*.gguf' --exclude='__pycache__' --exclude='cache' \
    -czf "$backup_dir/runtime-data.tar.gz"
  tar -tzf "$backup_dir/runtime-data.tar.gz" > "$backup_dir/runtime-data-archive-list.txt"
fi

if command -v pg_dump >/dev/null && [[ -n "${ARVECTUM_POSTGRES_DB:-}" ]]; then
  pg_host=${ARVECTUM_POSTGRES_HOST:-127.0.0.1}
  pg_port=${ARVECTUM_POSTGRES_PORT:-55432}
  if pg_dump -h "$pg_host" -p "$pg_port" -Fc -d "$ARVECTUM_POSTGRES_DB" -f "$backup_dir/postgres.dump" 2>"$backup_dir/postgres-backup.err"; then
    pg_restore --list "$backup_dir/postgres.dump" > "$backup_dir/postgres-restore-list.txt"
  else
    printf 'pg_dump failed; inspect postgres-backup.err locally.\n' > "$backup_dir/postgres-backup-failed.txt"
  fi
else
  printf 'PostgreSQL backup skipped: pg_dump or ARVECTUM_POSTGRES_DB is unavailable.\n' > "$backup_dir/postgres-backup-failed.txt"
fi

find "$backup_dir" -type f ! -name backup-manifest.sha256 -print0 | sort -z | xargs -0 shasum -a 256 > "$backup_dir/backup-manifest.sha256"
chmod -R go-rwx "$backup_dir"
printf '%s\n' "$backup_dir"
