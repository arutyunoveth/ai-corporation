#!/usr/bin/env bash
set -euo pipefail

usage() { echo "usage: $0 --backup DIR --target-project NAME --env-file FILE --compose-file FILE --port PORT [--replace]" >&2; exit 2; }
die() { echo "restore: $*" >&2; exit 1; }
backup= target= env_file= compose_file= port= replace=false
while (($#)); do
  case "$1" in
    --backup) backup=${2:-}; shift 2;; --target-project) target=${2:-}; shift 2;; --env-file) env_file=${2:-}; shift 2;;
    --compose-file) compose_file=${2:-}; shift 2;; --port) port=${2:-}; shift 2;; --replace) replace=true; shift;; -h|--help) usage;; *) usage;;
  esac
done
[[ -n "$backup" && -n "$target" && -n "$env_file" && -n "$compose_file" && -n "$port" ]] || usage
[[ "$target" != "arvectum-r7-staging" ]] || die "staging target is forbidden"
[[ "$port" != "18081" && "$port" =~ ^[0-9]+$ ]] || die "only a non-staging loopback port is allowed"
[[ -f "$backup/manifest.json" && -f "$backup/SHA256SUMS" && -f "$backup/database.dump" && -f "$backup/artifacts.tar.gz" ]] || die "incomplete backup package"
(cd "$backup" && shasum -a 256 -c SHA256SUMS) >/dev/null || die "backup checksum mismatch"
python3 - "$backup/manifest.json" "$backup/artifacts.tar.gz" <<'PY'
import json, pathlib, sys, tarfile
try:
    m=json.loads(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8'))
    assert m['manifest_version']==1 and m['accepted_run']['pdf_relative_path']
    with tarfile.open(sys.argv[2], 'r:gz') as a:
        for x in a.getmembers():
            if x.name.startswith('/') or '..' in pathlib.PurePosixPath(x.name).parts or x.isdev() or x.issym() or x.islnk(): raise ValueError(x.name)
except Exception as e: raise SystemExit(f'unsafe backup: {e}')
PY
existing=$(docker volume ls --format '{{.Name}}' | grep -E "^${target}_(pilot-db|pilot-data|pilot-artifacts|pilot-eis)$" || true)
if [[ -n "$existing" ]]; then
  $replace || die "target volumes already exist; pass --replace only for a disposable non-staging target"
  docker compose --project-name "$target" --env-file "$env_file" -f "$compose_file" down || true
  while IFS= read -r volume; do docker volume rm "$volume"; done <<< "$existing"
fi
override=$(mktemp)
trap 'rm -f "$override"' EXIT
printf 'services:\n  pilot-proxy:\n    ports: !override ["127.0.0.1:%s:8080"]\n' "$port" > "$override"
compose=(docker compose --project-name "$target" --env-file "$env_file" -f "$compose_file" -f "$override")
"${compose[@]}" up -d pilot-db
for _ in {1..30}; do "${compose[@]}" exec -T pilot-db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null && break; sleep 2; done
"${compose[@]}" exec -T pilot-db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null || die "target DB is unhealthy"
"${compose[@]}" exec -T pilot-db sh -lc 'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' < "$backup/database.dump"
for volume in pilot-data pilot-artifacts pilot-eis; do
  docker volume create "${target}_${volume}" >/dev/null
done
docker run --rm -v "${target}_pilot-data:/restore/data" -v "${target}_pilot-artifacts:/restore/artifacts" -v "${target}_pilot-eis:/restore/eis-archives" -v "$backup:/backup:ro" alpine:3.20 sh -ec 'tar -xzf /backup/artifacts.tar.gz -C /restore'
python3 - "$backup/manifest.json" "$target" <<'PY'
import json, sys
m=json.load(open(sys.argv[1], encoding='utf-8'))
print(m['accepted_run']['pdf_relative_path'])
PY
pdf_rel=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["accepted_run"]["pdf_relative_path"])' "$backup/manifest.json")
vol_pdf_sha=$(docker run --rm -v "${target}_pilot-data:/restore/data:ro" alpine:3.20 sh -ec "sha256sum /restore/$pdf_rel" | awk '{print $1}')
expected_sha=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["accepted_run"]["pdf_sha256"])' "$backup/manifest.json")
[[ "$vol_pdf_sha" == "$expected_sha" ]] || die "restored PDF hash mismatch"
"${compose[@]}" up -d pilot-migrate pilot-eis-preflight pilot-api pilot-proxy
echo "restore started: $target on 127.0.0.1:$port"
