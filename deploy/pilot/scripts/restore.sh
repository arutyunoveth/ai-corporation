#!/usr/bin/env bash
set -euo pipefail
usage() { echo "usage: $0 --backup DIR --target-project NAME --env-file FILE --compose-file FILE --trust-dir DIR --port PORT [--replace]" >&2; exit 2; }
die() { echo "restore: $*" >&2; exit 1; }
backup= target= env_file= compose_file= trust_dir= port= replace=false
while (($#)); do case "$1" in --backup) backup=${2:-};shift 2;;--target-project) target=${2:-};shift 2;;--env-file) env_file=${2:-};shift 2;;--compose-file) compose_file=${2:-};shift 2;;--trust-dir) trust_dir=${2:-};shift 2;;--port) port=${2:-};shift 2;;--replace) replace=true;shift;;*) usage;;esac;done
[[ -n "$backup" && -n "$target" && -n "$env_file" && -n "$compose_file" && -n "$trust_dir" && -n "$port" ]] || usage
[[ "$target" =~ ^[a-z0-9][a-z0-9_-]*$ ]] || die "invalid target project"
[[ "$target" != arvectum-r7-staging && "$port" != 18081 && "$port" =~ ^[0-9]+$ ]] || die "staging target or port is forbidden"
[[ -f "$backup/manifest.json" && -f "$backup/SHA256SUMS" && -f "$backup/database.dump" && -f "$backup/artifacts.tar.gz" && -f "$env_file" && -d "$trust_dir" ]] || die "incomplete input"
(cd "$backup" && shasum -a 256 -c SHA256SUMS) >/dev/null || die "backup checksum mismatch"
source_project=$(python3 -c 'import json,sys; m=json.load(open(sys.argv[1])); assert m.get("manifest_version")==1; print(m.get("source_project", ""))' "$backup/manifest.json") || die "malformed manifest"
[[ -n "$source_project" && "$target" != "$source_project" ]] || die "target must differ from source project"
python3 - "$backup/artifacts.tar.gz" <<'PY'
import pathlib,sys,tarfile
with tarfile.open(sys.argv[1],'r:gz') as a:
 for x in a.getmembers():
  if x.name.startswith('/') or '..' in pathlib.PurePosixPath(x.name).parts or x.isdev() or x.issym() or x.islnk(): raise SystemExit('unsafe artifact archive')
PY
volumes=("${target}_pilot-db" "${target}_pilot-data" "${target}_pilot-artifacts" "${target}_pilot-eis")
existing=(); for volume in "${volumes[@]}"; do docker volume inspect "$volume" >/dev/null 2>&1 && existing+=("$volume"); done
if ((${#existing[@]})); then $replace || die "target volumes already exist; pass --replace"; env "PILOT_SECRET_ENV=$env_file" "PILOT_CONTAINER_TRUST=$trust_dir" docker compose --project-name "$target" --env-file "$env_file" -f "$compose_file" down || true; docker volume rm "${existing[@]}"; fi
override=$(mktemp); trap 'rm -f "$override"' EXIT; printf 'services:\n  pilot-proxy:\n    ports: !override ["127.0.0.1:%s:8080"]\n' "$port" > "$override"
compose=(env "PILOT_SECRET_ENV=$env_file" "PILOT_CONTAINER_TRUST=$trust_dir" docker compose --project-name "$target" --env-file "$env_file" -f "$compose_file" -f "$override")
"${compose[@]}" up -d pilot-db
for _ in {1..30}; do "${compose[@]}" exec -T pilot-db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null && break; sleep 2; done
"${compose[@]}" exec -T pilot-db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null || die "target DB health timeout"
"${compose[@]}" exec -T pilot-db sh -lc 'exec pg_restore -U "$POSTGRES_USER" -d "$POSTGRES_DB" --clean --if-exists --no-owner --no-privileges' < "$backup/database.dump"
expected_head=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["alembic"]["repository_head"])' "$backup/manifest.json") || die "missing Alembic metadata"
restored_head=$("${compose[@]}" exec -T pilot-db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT version_num FROM alembic_version"' | tr -d '[:space:]')
[[ "$restored_head" == "$expected_head" ]] || die "restored Alembic head mismatch"
for volume in "${volumes[@]:1}"; do docker volume create "$volume" >/dev/null; done
docker run --rm -v "${target}_pilot-data:/restore/data" -v "${target}_pilot-artifacts:/restore/artifacts" -v "${target}_pilot-eis:/restore/eis-archives" -v "$backup:/backup:ro" alpine:3.20 sh -ec 'tar -xzf /backup/artifacts.tar.gz -C /restore'
"${compose[@]}" up -d --build pilot-migrate pilot-eis-preflight pilot-api pilot-proxy
for _ in {1..45}; do [[ $(docker inspect -f '{{.State.Health.Status}}' "${target}-pilot-api-1" 2>/dev/null || true) == healthy ]] && break; sleep 2; done
[[ $(docker inspect -f '{{.State.Health.Status}}' "${target}-pilot-api-1" 2>/dev/null || true) == healthy ]] || die "API health timeout"
curl --noproxy '*' -fsS "http://127.0.0.1:$port/health/tender-agent" >/dev/null || die "proxy health timeout"
run_id=$(python3 -c 'import json,sys; x=json.load(open(sys.argv[1])).get("accepted_run"); print(x.get("run_id", "") if isinstance(x,dict) else "")' "$backup/manifest.json")
if [[ -n "$run_id" ]]; then
  verify_tmp=$(mktemp -d); trap 'rm -f "$override"; rm -rf "$verify_tmp"' EXIT
  set -a; source "$env_file"; set +a
  pdf_rel=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["accepted_run"]["pdf_relative_path"] if "pdf_relative_path" in json.load(open(sys.argv[1]))["accepted_run"] else "")' "$backup/manifest.json")
  expected=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["accepted_run"]["pdf_sha256"])' "$backup/manifest.json")
  before=$(docker run --rm -v "${target}_pilot-data:/data:ro" alpine:3.20 sh -ec "stat -c '%Y:%s' /data/${pdf_rel#data/}")
  curl --noproxy '*' -fsS -u "$AI_CORP_PILOT_AUTH_USERNAME:$AI_CORP_PILOT_AUTH_PASSWORD" "http://127.0.0.1:$port/api/demo/tender-agent/runs/$run_id/export/pdf" -o "$verify_tmp/restored.pdf"
  [[ $(shasum -a 256 "$verify_tmp/restored.pdf" | awk '{print $1}') == "$expected" ]] || die "restored PDF hash mismatch"
  after=$(docker run --rm -v "${target}_pilot-data:/data:ro" alpine:3.20 sh -ec "stat -c '%Y:%s' /data/${pdf_rel#data/}")
  [[ "$before" == "$after" ]] || die "restored PDF mtime changed"
fi
echo "restore verified"
