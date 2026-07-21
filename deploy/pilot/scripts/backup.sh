#!/usr/bin/env bash
set -euo pipefail

usage() { echo "usage: $0 --output DIR --project-name NAME --env-file FILE --compose-file FILE [--run-id ID]" >&2; exit 2; }
die() { echo "backup: $*" >&2; exit 1; }

output= project= env_file= compose_file= run_id="${PILOT_ACCEPTED_RUN_ID:-toa-run-20260721144956-8b2eee}"
while (($#)); do
  case "$1" in
    --output) output=${2:-}; shift 2;; --project-name) project=${2:-}; shift 2;;
    --env-file) env_file=${2:-}; shift 2;; --compose-file) compose_file=${2:-}; shift 2;;
    --run-id) run_id=${2:-}; shift 2;; -h|--help) usage;; *) usage;;
  esac
done
[[ -n "$output" && -n "$project" && -n "$env_file" && -n "$compose_file" ]] || usage
[[ -f "$env_file" && -f "$compose_file" ]] || die "env file or compose file is missing"
command -v docker >/dev/null || die "docker is unavailable"
[[ ! -e "$output" ]] || die "output path already exists"
mkdir -p "$(dirname "$output")"

compose=(docker compose --project-name "$project" --env-file "$env_file" -f "$compose_file")
"${compose[@]}" ps --status running pilot-db | grep -q pilot-db || die "pilot-db is not running"
"${compose[@]}" ps --status running pilot-api | grep -q pilot-api || die "pilot-api is not running"
"${compose[@]}" exec -T pilot-db sh -lc 'pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"' >/dev/null || die "pilot-db is unhealthy"
api_id=$("${compose[@]}" ps -q pilot-api)
[[ -n "$api_id" ]] || die "pilot-api container is missing"

tmp=$(mktemp -d "${output%/}.tmp.XXXXXX")
cleanup() { rm -rf "$tmp"; }
trap cleanup EXIT

"${compose[@]}" exec -T pilot-db sh -lc 'exec pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc --no-owner --no-privileges' > "$tmp/database.dump"
[[ -s "$tmp/database.dump" ]] || die "pg_dump produced an empty dump"
"${compose[@]}" exec -T pilot-db pg_restore --list < "$tmp/database.dump" >/dev/null || die "pg_restore validation failed"

pdf_rel="data/demo/exports/demo_agent_report_0379100000726000101_toa-run-.pdf"
pdf_host="$tmp/accepted.pdf"
docker cp "$api_id:/app/$pdf_rel" "$pdf_host" || die "persisted PDF is missing"
[[ $(head -c 5 "$pdf_host") == '%PDF-' ]] || die "persisted PDF is invalid"
pdf_sha=$(shasum -a 256 "$pdf_host" | awk '{print $1}')
[[ "$pdf_sha" == "2a09d8e4985f9167dd9a5a7dd7ca384499b5dcc70ca4fd328210aaf9002cb94d" ]] || die "persisted PDF hash differs from accepted baseline"
report_sha=$(docker exec "$api_id" sh -lc "sha256sum /app/artifacts/tender_operator_demo/$run_id/output/canonical_report.json" | awk '{print $1}')

docker run --rm --volumes-from "$api_id:ro" -v "$tmp:/backup" alpine:3.20 sh -ec '
  tar -C /app --exclude="*.tmp" --exclude="*.partial" --exclude="*.part" -czf /backup/artifacts.tar.gz data artifacts eis-archives
'
[[ -s "$tmp/artifacts.tar.gz" ]] || die "artifact archive is empty"
tar -tzf "$tmp/artifacts.tar.gz" | grep -qx "$pdf_rel" || die "archive misses persisted PDF"
archive_pdf_sha=$(tar -xOzf "$tmp/artifacts.tar.gz" "$pdf_rel" | shasum -a 256 | awk '{print $1}')
[[ "$archive_pdf_sha" == "$pdf_sha" ]] || die "archived PDF hash mismatch"

db_sha=$(shasum -a 256 "$tmp/database.dump" | awk '{print $1}')
art_sha=$(shasum -a 256 "$tmp/artifacts.tar.gz" | awk '{print $1}')
app_commit=$(git rev-parse HEAD)
tree_sha=$(git rev-parse HEAD^{tree})
alembic_head=$(docker exec "$api_id" alembic heads 2>/dev/null | awk 'NR==1 {print $1}')
python3 - "$tmp/manifest.json" "$project" "$app_commit" "$tree_sha" "$alembic_head" "$db_sha" "$art_sha" "$tmp/database.dump" "$tmp/artifacts.tar.gz" "$run_id" "$report_sha" "$pdf_rel" "$pdf_host" "$pdf_sha" <<'PY'
import json, pathlib, sys
p=pathlib.Path
(out, project, commit, tree, head, dbsha, artsha, db, art, run, reportsha, pdfrel, pdf, pdfsha)=sys.argv[1:]
payload={"manifest_version":1,"created_at_utc":__import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),"source_project":project,"release_baseline_commit":"c0e7c7dbfb65765e5a918318d784115b00b4ce06","application_commit":commit,"application_tree_sha":tree,"alembic_head":head,"database_dump":{"filename":"database.dump","byte_size":p(db).stat().st_size,"sha256":dbsha,"format":"pg_dump custom (-Fc)"},"artifacts_archive":{"filename":"artifacts.tar.gz","byte_size":p(art).stat().st_size,"sha256":artsha},"accepted_run":{"run_id":run,"procurement_number":"0379100000726000101","report_model_hash":reportsha,"pdf_relative_path":pdfrel,"pdf_size":p(pdf).stat().st_size,"pdf_sha256":pdfsha},"external_prerequisites":{"eis_root_sha256":"C2A80C62195278A6636DE9DE1ECDA45EE7E929FB8E2EC74B3A5ABD7F4A1129F3","eis_intermediate_sha256":"2155785036C900DBB5F1BB2A1569C80C55595BD6BF94867A29BBDDBC7D88A3F2","certificates_not_included":True}}
p(out).write_text(json.dumps(payload, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
PY
(cd "$tmp" && shasum -a 256 database.dump artifacts.tar.gz manifest.json > SHA256SUMS)
(cd "$tmp" && shasum -a 256 -c SHA256SUMS) >/dev/null || die "checksum validation failed"
mv "$tmp" "$output"
trap - EXIT
echo "backup created: $output"
