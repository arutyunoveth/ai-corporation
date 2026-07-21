#!/usr/bin/env bash
set -euo pipefail

usage() { echo "usage: $0 --output DIR --project-name NAME --env-file FILE --compose-file FILE --trust-dir DIR [--verify-run-id ID --expected-pdf-sha256 SHA256]" >&2; exit 2; }
die() { echo "backup: $*" >&2; exit 1; }
output= project= env_file= compose_file= trust_dir= verify_run= expected_pdf=
while (($#)); do case "$1" in
  --output) output=${2:-}; shift 2;; --project-name) project=${2:-}; shift 2;; --env-file) env_file=${2:-}; shift 2;; --compose-file) compose_file=${2:-}; shift 2;; --trust-dir) trust_dir=${2:-}; shift 2;; --verify-run-id) verify_run=${2:-}; shift 2;; --expected-pdf-sha256) expected_pdf=${2:-}; shift 2;; *) usage;; esac; done
[[ -n "$output" && -n "$project" && -n "$env_file" && -n "$compose_file" && -n "$trust_dir" ]] || usage
[[ -f "$env_file" && -f "$compose_file" && -d "$trust_dir" && ! -e "$output" ]] || die "invalid input path or existing output"
[[ -z "$expected_pdf" || -n "$verify_run" ]] || die "--expected-pdf-sha256 requires --verify-run-id"
compose=(env "PILOT_SECRET_ENV=$env_file" "PILOT_CONTAINER_TRUST=$trust_dir" docker compose --project-name "$project" --env-file "$env_file" -f "$compose_file")
"${compose[@]}" ps --status running pilot-db | grep -q pilot-db || die "pilot-db is not running"
"${compose[@]}" ps --status running pilot-api | grep -q pilot-api || die "pilot-api is not running"
"${compose[@]}" exec -T pilot-db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null || die "pilot-db is unhealthy"
api_id=$("${compose[@]}" ps -q pilot-api); [[ -n "$api_id" ]] || die "pilot-api container is missing"
repo_head=$(docker exec "$api_id" alembic heads 2>/dev/null | awk 'NF {print $1}')
db_head=$("${compose[@]}" exec -T pilot-db sh -lc 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Atqc "SELECT version_num FROM alembic_version"' | tr -d '[:space:]')
[[ "$repo_head" =~ ^[A-Za-z0-9_]+$ && "$db_head" =~ ^[A-Za-z0-9_]+$ && "$repo_head" == "$db_head" ]] || die "repository and database Alembic heads must match"
mkdir -p "$(dirname "$output")"; tmp=$(mktemp -d "${output%/}.tmp.XXXXXX"); trap 'rm -rf "$tmp"' EXIT
"${compose[@]}" exec -T pilot-db sh -lc 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges' > "$tmp/database.dump"
[[ -s "$tmp/database.dump" ]] && "${compose[@]}" exec -T pilot-db pg_restore --list < "$tmp/database.dump" >/dev/null || die "database dump validation failed"
docker run --rm --volumes-from "$api_id:ro" -v "$tmp:/backup" alpine:3.20 sh -ec 'tar -C /app --exclude="*.tmp" --exclude="*.partial" --exclude="*.part" -czf /backup/artifacts.tar.gz data artifacts eis-archives'
[[ -s "$tmp/artifacts.tar.gz" ]] || die "artifact archive is empty"
db_sha=$(shasum -a 256 "$tmp/database.dump" | awk '{print $1}'); art_sha=$(shasum -a 256 "$tmp/artifacts.tar.gz" | awk '{print $1}')
if [[ -n "$verify_run" ]]; then
  manifest_path=$(docker exec "$api_id" sh -lc "grep -rl --include='*.manifest.json' --fixed-strings '\"run_id\": \"$verify_run\"' /app/data/demo/exports 2>/dev/null | head -1")
  [[ -n "$manifest_path" ]] || die "no PDF artifact manifest for requested run"
  docker cp "$api_id:$manifest_path" "$tmp/selected.manifest.json"
else printf 'null\n' > "$tmp/selected.manifest.json"; fi
python3 - "$tmp/manifest.json" "$tmp/selected.manifest.json" "$tmp/database.dump" "$tmp/artifacts.tar.gz" "$project" "$trust_dir" "$verify_run" "$expected_pdf" "$repo_head" "$db_head" <<'PY'
import hashlib,json,pathlib,re,sys,datetime
out,selected,db,art,project,trust,run,expected,repo_head,db_head=sys.argv[1:]
chosen=json.load(open(selected))
if run:
    if not isinstance(chosen,dict) or chosen.get('run_id')!=run: raise SystemExit('selected artifact manifest is invalid')
    if expected and chosen.get('pdf_sha256','').lower()!=expected.lower(): raise SystemExit('selected PDF hash differs from expected')
policy=pathlib.Path(trust)/'policy.yaml'; policy_text=policy.read_text(encoding='utf-8') if policy.is_file() else ''
fingerprints=re.findall(r'(?i)\b[0-9a-f]{64}\b',policy_text)
sha=lambda p: hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
payload={'manifest_version':1,'created_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'source_project':project,'release_baseline_commit':'c0e7c7dbfb65765e5a918318d784115b00b4ce06','application_commit':__import__('subprocess').check_output(['git','rev-parse','HEAD'],text=True).strip(),'application_tree_sha':__import__('subprocess').check_output(['git','rev-parse','HEAD^{tree}'],text=True).strip(),'alembic':{'repository_head':repo_head,'database_head':db_head,'matched':True},'database_dump':{'filename':'database.dump','byte_size':pathlib.Path(db).stat().st_size,'sha256':sha(db),'format':'pg_dump custom (-Fc)'},'artifacts_archive':{'filename':'artifacts.tar.gz','byte_size':pathlib.Path(art).stat().st_size,'sha256':sha(art)},'accepted_run':chosen,'external_prerequisites':{'certificate_sha256':fingerprints,'certificates_not_included':True}}
pathlib.Path(out).write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
PY
(cd "$tmp" && shasum -a 256 database.dump artifacts.tar.gz manifest.json > SHA256SUMS && shasum -a 256 -c SHA256SUMS >/dev/null) || die "checksum validation failed"
mv "$tmp" "$output"; trap - EXIT; echo "backup created: $output"
