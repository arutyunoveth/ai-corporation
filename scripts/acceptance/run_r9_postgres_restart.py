"""Fail-closed R9.2 smoke: published customer result across PostgreSQL stop/start."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts" / "acceptance")]
from run_r8_acceptance import _enrich_states, _prepare_customer, _seed, snapshot_filesystem  # noqa: E402
from r8_acceptance.runtime import free_port  # noqa: E402
from run_r9_application_restart import (  # noqa: E402
    COMPOSE, CUSTOMER, cleanup_runtime, fetch_db_artifact_binding, fetch_http_snapshot,
    fetch_verifier_snapshot, health_status, revision, run_command, run_hygiene_self_test,
    sanitize_text, sanitize_value, scan_hygiene, snapshot_database, start_uvicorn,
    stop_uvicorn, utcnow, wait_for_health, write_json, write_sums,
)

SUCCESS = "R9_2_POSTGRESQL_RESTART_SMOKE_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL"
FILES = ("postgres-restart-result.json", "postgres-lifecycle.json", "application-lifecycle.json", "post-restart-operations.json", "volume-identity.json", "http-snapshots.json", "database-snapshots.json", "filesystem-snapshots.json", "verifier-results.json", "postgres-identity.json", "backend-first.log", "backend-second.log", "commands.log", "cleanup.json", "SHA256SUMS")


def inspect_postgres(project: str) -> dict[str, Any]:
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    cid = subprocess.run(compose + ["ps", "-aq", "postgres"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    raw = subprocess.run(["docker", "inspect", cid], text=True, capture_output=True, check=True).stdout
    item = json.loads(raw)[0]
    mount = next(m for m in item["Mounts"] if m["Destination"] == "/var/lib/postgresql/data")
    volume = json.loads(subprocess.run(["docker", "volume", "inspect", mount["Name"]], text=True, capture_output=True, check=True).stdout)[0]
    state = item["State"]
    return {"container_id": item["Id"], "container_name": item["Name"], "started_at": state.get("StartedAt"), "restart_count": state.get("RestartCount"), "running": state.get("Running"), "health": state.get("Health", {}).get("Status"), "compose_project": project, "service": "postgres", "volume_name": mount["Name"], "volume_mountpoint": volume["Mountpoint"], "volume_created_at": volume["CreatedAt"], "volume_labels": volume.get("Labels"), "mount_source": mount["Source"], "mount_destination": mount["Destination"]}


def sql_identity(env: dict[str, str], commands: list[dict[str, Any]], secrets_map: dict[str, str], check: bool = True) -> dict[str, Any]:
    code = """import json,os
from sqlalchemy import create_engine,text
e=create_engine(os.environ['AI_CORP_DATABASE_URL'])
with e.connect() as c:
 q=text(\"select current_database(),current_user,version(),(select system_identifier from pg_control_system())\")
 r=c.execute(q).one();print(json.dumps({'database':r[0],'user':r[1],'version':r[2],'system_identifier':r[3]}))"""
    result = run_command([sys.executable, "-c", code], env, commands, secrets_map, check=check)
    return {"at": utcnow(), "exit_code": result.returncode, "success": result.returncode == 0, "identity": json.loads(result.stdout) if result.returncode == 0 else None, "stdout": sanitize_text(result.stdout, secrets_map), "stderr": sanitize_text(result.stderr, secrets_map)}


def wait_for_postgres(project: str, env: dict[str, str], commands: list[dict[str, Any]], secrets_map: dict[str, str]) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        identity = inspect_postgres(project)
        probe = sql_identity(env, commands, secrets_map, check=False)
        if identity["running"] and identity["health"] == "healthy" and probe["success"]:
            return identity, probe
        time.sleep(0.25)
    raise TimeoutError("PostgreSQL did not become healthy and SQL-ready")


def snapshot_filesystem_stable(root: Path) -> dict[str, Any]:
    """Directory mtimes are normalized because Docker volume remount rounds them."""
    snapshot = snapshot_filesystem(root)
    for item in snapshot.values():
        if item.get("type") == "directory":
            item.pop("mtime_ns", None)
    return snapshot


def assertions(data: dict[str, Any]) -> dict[str, bool]:
    pre, post = data.get("http", {}).get("pre", {}), data.get("http", {}).get("post", {})
    first, second = data["application"]["first"], data["application"]["second"]
    pgpre, pgpost = data.get("postgres", {}).get("pre", {}), data.get("postgres", {}).get("post", {})
    stopped = data.get("postgres", {}).get("stopped", {})
    volume_pre, volume_post = data.get("volume", {}).get("pre", {}), data.get("volume", {}).get("post", {})
    a_pre, a_post = pre.get("artifacts", []), post.get("artifacts", [])
    fields = ("id", "artifact_type", "artifact_key", "report_model_hash", "renderer_version", "pdf_sha256", "byte_size", "immutable_at", "status")
    cases_equal = all(pre.get("case", {}).get(k) == post.get("case", {}).get(k) for k in ("id", "customer_id", "project_id", "artifact_key"))
    runs = pre.get("case", {}).get("runs", []), post.get("case", {}).get("runs", [])
    runs_equal = len(runs[0]) == len(runs[1]) == 1 and runs[0][0].get("id") == runs[1][0].get("id") == data["state"].get("run_id") and runs[0][0].get("status") == runs[1][0].get("status") == "completed"
    binding = data.get("binding", {})
    normalize = lambda x: x.isoformat() if hasattr(x, "isoformat") else str(x)
    db = data.get("database", {})
    def parsed(value: Any) -> datetime | None:
        try:
            item = datetime.fromisoformat(str(value))
            return item if item.tzinfo is not None else None
        except (TypeError, ValueError): return None
    first_exit, pg_stop, pg_ready, second_start = parsed(first.get("exited_at")), parsed(data["postgres_lifecycle"].get("stop_requested_at")), parsed(data["postgres_lifecycle"].get("sql_ready_at")), parsed(second.get("start_requested_at"))
    sql_pre, sql_post, sql_down = data.get("sql", {}).get("pre", {}), data.get("sql", {}).get("post", {}), data.get("sql", {}).get("unavailable", {})
    operations = data.get("post_restart_operations", [])
    return {
        "postgres_initially_healthy": pgpre.get("running") is True and pgpre.get("health") == "healthy",
        "application_stopped_before_postgres_stop": first.get("process_exited") is True and first_exit is not None and pg_stop is not None and first_exit <= pg_stop,
        "postgres_stop_exit_zero": data["postgres_lifecycle"].get("stop_exit_code") == 0,
        "postgres_unavailable_while_stopped": sql_down.get("exit_code", 0) != 0 and sql_down.get("identity") is None and stopped.get("running") is False,
        "postgres_container_exists_while_stopped": bool(stopped.get("container_id")),
        "postgres_container_not_running_while_stopped": stopped.get("running") is False,
        "postgres_start_exit_zero": data["postgres_lifecycle"].get("start_exit_code") == 0,
        "postgres_healthy_after_start": pgpost.get("running") is True and pgpost.get("health") == "healthy",
        "postgres_sql_ready_after_start": bool(data.get("sql", {}).get("post")),
        "postgres_container_id_preserved": bool(pgpre.get("container_id")) and pgpre.get("container_id") == stopped.get("container_id") == pgpost.get("container_id") and pgpre.get("container_name") == stopped.get("container_name") == pgpost.get("container_name") and pgpre.get("compose_project") == stopped.get("compose_project") == pgpost.get("compose_project") and pgpre.get("service") == stopped.get("service") == pgpost.get("service"),
        "postgres_started_at_changed": pgpre.get("started_at") != pgpost.get("started_at"),
        "postgres_volume_name_preserved": bool(volume_pre.get("volume_name")) and volume_pre.get("volume_name") == data["volume"].get("stopped", {}).get("volume_name") == volume_post.get("volume_name"),
        "postgres_volume_mountpoint_preserved": bool(volume_pre.get("volume_mountpoint")) and volume_pre.get("volume_mountpoint") == data["volume"].get("stopped", {}).get("volume_mountpoint") == volume_post.get("volume_mountpoint"),
        "postgres_volume_created_at_preserved": bool(volume_pre.get("volume_created_at")) and volume_pre.get("volume_created_at") == data["volume"].get("stopped", {}).get("volume_created_at") == volume_post.get("volume_created_at"),
        "postgres_mount_binding_preserved": bool(volume_pre.get("mount_source")) and all((volume_pre.get(k), volume_pre.get("mount_destination")) == (item.get(k), item.get("mount_destination")) for item in (data["volume"].get("stopped", {}), volume_post) for k in ("mount_source",)),
        "postgres_volume_labels_preserved": bool(volume_pre.get("volume_labels")) and volume_pre.get("volume_labels") == data["volume"].get("stopped", {}).get("volume_labels") == volume_post.get("volume_labels"),
        "postgres_system_identifier_preserved": bool(sql_pre.get("identity", {}).get("system_identifier")) and sql_pre.get("identity", {}).get("system_identifier") == sql_post.get("identity", {}).get("system_identifier"),
        "postgres_database_identity_preserved": sql_pre.get("success") is True and sql_post.get("success") is True and all(sql_pre.get("identity", {}).get(k) and sql_pre.get("identity", {}).get(k) == sql_post.get("identity", {}).get(k) for k in ("database", "user", "version", "system_identifier")),
        "alembic_revision_preserved": data.get("revision", {}).get("pre") == data.get("revision", {}).get("post") == "096_add_r8_canonical_snapshot_binding",
        "first_health_200": first.get("health_status") == 200,
        "first_health_unavailable_after_stop": data.get("first_health_after_stop") is None,
        "second_health_200": second.get("health_status") == 200,
        "different_application_pids": first.get("pid") is not None and first.get("pid") != second.get("pid"),
        "first_application_exited_before_postgres_stop": first_exit is not None and pg_stop is not None and first_exit <= pg_stop,
        "second_application_started_after_postgres_ready": second_start is not None and pg_ready is not None and second_start >= pg_ready,
        "case_http_identity_preserved": pre.get("case_status") == post.get("case_status") == 200 and cases_equal and runs_equal and pre.get("case", {}).get("status") == post.get("case", {}).get("status") == "delivered",
        "lifecycle_http_preserved": pre.get("case", {}).get("status") == post.get("case", {}).get("status") == "delivered",
        "artifact_http_identity_preserved": pre.get("artifacts_status") == post.get("artifacts_status") == 200 and len(a_pre) == len(a_post) == 1 and all(a_pre[0].get(k) == a_post[0].get(k) for k in fields) and all(normalize(a_post[0].get(k)) == normalize(binding.get(k)) for k in fields),
        "pdf_bytes_equal": pre.get("pdf_sha256") == post.get("pdf_sha256") and pre.get("pdf_byte_size") == post.get("pdf_byte_size"),
        "pdf_hash_matches_db": pre.get("pdf_sha256") == post.get("pdf_sha256") == binding.get("pdf_sha256"),
        "pdf_size_matches_db": pre.get("pdf_byte_size") == post.get("pdf_byte_size") == binding.get("byte_size"),
        "db_snapshots_equal": db.get("pre") == db.get("post"), "filesystem_snapshots_equal": data.get("filesystem", {}).get("pre") == data.get("filesystem", {}).get("post"),
        "canonical_verifier_pass_pre_post": data.get("verifier", {}).get("pre", {}).get("canonical") == data.get("verifier", {}).get("post", {}).get("canonical") == "PASS",
        "artifact_verifier_pass_pre_post": data.get("verifier", {}).get("pre", {}).get("artifact") == data.get("verifier", {}).get("post", {}).get("artifact") == "PASS",
        "review_verifier_pass_pre_post": data.get("verifier", {}).get("pre", {}).get("review") == data.get("verifier", {}).get("post", {}).get("review") == "PASS",
        "one_run_result": db.get("pre", {}).get("business", {}).get("PilotRunResult", {}).get("count") == 1,
        "one_final_artifact": db.get("pre", {}).get("business", {}).get("PilotArtifact", {}).get("count") == 1,
        "one_review": db.get("pre", {}).get("business", {}).get("PilotReview", {}).get("count") == 1,
        "no_canonical_partials": not any(".analysis.partial." in p for p in data.get("filesystem", {}).get("pre", {})),
        "no_artifact_partials": not any(".artifact." in p and ".partial." in p for p in data.get("filesystem", {}).get("pre", {})),
        "audit_unchanged": db.get("pre", {}).get("audit_count") == db.get("post", {}).get("audit_count"),
        "no_post_restart_mutations": bool(operations) and all(item.get("read_only") is True and item.get("method") not in {"POST", "PUT", "PATCH", "DELETE"} for item in operations) and db.get("pre") == db.get("post"),
        "both_application_processes_exited": all(item.get("process_exited") is True for item in (first, second)),
        "both_application_return_codes_recorded": all(item.get("return_code") is not None for item in (first, second)),
        "application_termination_expected": all(item.get("return_code") in {-15, -9} and item.get("termination_method") in {"SIGTERM", "SIGKILL"} for item in (first, second)),
        "cleanup_errors_empty": data.get("cleanup_errors", []) == [], "cleanup_complete": False, "evidence_pack_complete": False, "sha256sums_complete_and_valid": False, "evidence_hygiene_pass": False,
    }


def main() -> int:
    evidence = ROOT / "output" / f"r9-postgres-restart-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    evidence.mkdir(parents=True); temporary = Path(tempfile.mkdtemp(prefix="r9-pg-", dir=ROOT / "output")); data_root = temporary / "data"; data_root.mkdir()
    pg_port, api_port, password, project = free_port(), free_port(), "r9-" + secrets.token_urlsafe(20), "r9pg" + secrets.token_hex(5)
    dsn = f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{pg_port}/r8_acceptance"
    secrets_map = {"password": password, "temporary_root": str(temporary), "database_url": dsn, "authorization": "Authorization: Basic Og=="}
    env = os.environ.copy(); env.update({"R8_POSTGRES_PASSWORD": password, "R8_POSTGRES_PORT": str(pg_port), "AI_CORP_DATABASE_URL": dsn, "AI_CORP_ARVECTUM_DATA_DIR": str(data_root), "AI_CORP_PILOT_AUTH_ENABLED": "false", "AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED": "false"})
    commands: list[dict[str, Any]] = []; data: dict[str, Any] = {"state": {}, "application": {"first": {}, "second": {}}, "postgres_lifecycle": {}, "postgres": {}, "volume": {}, "sql": {}, "http": {}, "database": {}, "filesystem": {}, "verifier": {}, "cleanup": {}, "cleanup_errors": [], "post_restart_operations": []}
    first = second = None
    try:
        compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
        run_command(compose + ["up", "-d", "--wait"], env, commands, secrets_map)
        run_command([sys.executable, "-m", "alembic", "upgrade", "096_add_r8_canonical_snapshot_binding"], env, commands, secrets_map)
        data["revision"] = {"pre": revision(env, commands, secrets_map)}; _seed(env)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from src.modules.customer_registry.models import CustomerProfile
        with Session(create_engine(dsn)) as session: session.add(CustomerProfile(customer_id=CUSTOMER, legal_name="R9 synthetic customer", customer_status="prospect")); session.commit()
        first = start_uvicorn(env, api_port, evidence / "backend-first.log", data["application"]["first"])
        if wait_for_health(first, api_port, data["application"]["first"]) != 200: raise RuntimeError("first health failed")
        base = f"http://127.0.0.1:{api_port}/api/operator/pilot/customers/{CUSTOMER}"; data["state"] = _prepare_customer("http://127.0.0.1:%s/api/operator/pilot/customers/{customer}" % api_port, "", "", CUSTOMER); _enrich_states(env, [data["state"]])
        data["http"]["pre"] = fetch_http_snapshot(base, data["state"]); data["database"]["pre"] = snapshot_database(env); data["filesystem"]["pre"] = snapshot_filesystem_stable(data_root); data["verifier"]["pre"] = fetch_verifier_snapshot(env, data["state"]); data["binding"] = fetch_db_artifact_binding(env, data["state"]); data["postgres_lifecycle"]["pre_identity_at"] = utcnow(); data["postgres"]["pre"] = inspect_postgres(project); data["volume"]["pre"] = data["postgres"]["pre"]; data["sql"]["pre"] = sql_identity(env, commands, secrets_map)
        stop_uvicorn(first, data["application"]["first"]); data["first_health_after_stop"] = health_status(api_port)
        data["postgres_lifecycle"]["stop_requested_at"] = utcnow(); stopped = run_command(compose + ["stop", "postgres"], env, commands, secrets_map); data["postgres_lifecycle"]["stop_exit_code"] = stopped.returncode; data["postgres_lifecycle"]["stopped_at"] = utcnow(); data["postgres"]["stopped"] = inspect_postgres(project); data["volume"]["stopped"] = data["postgres"]["stopped"]
        data["postgres_lifecycle"]["unavailable_probe_at"] = utcnow(); data["sql"]["unavailable"] = sql_identity(env, commands, secrets_map, check=False); data["postgres_lifecycle"]["unavailable_probe_return_code"] = data["sql"]["unavailable"]["exit_code"]
        data["postgres_lifecycle"]["start_requested_at"] = utcnow(); started = run_command(compose + ["start", "postgres"], env, commands, secrets_map); data["postgres_lifecycle"]["start_exit_code"] = started.returncode; data["postgres"]["post"], data["sql"]["post"] = wait_for_postgres(project, env, commands, secrets_map); data["volume"]["post"] = data["postgres"]["post"]; data["postgres_lifecycle"]["healthy_at"] = utcnow(); data["postgres_lifecycle"]["sql_ready_at"] = utcnow(); data["postgres_lifecycle"]["post_identity_at"] = utcnow(); data["revision"]["post"] = revision(env, commands, secrets_map); data["post_restart_operations"].append({"at": utcnow(), "operation": "alembic_revision", "method": "SELECT", "read_only": True})
        second = start_uvicorn(env, api_port, evidence / "backend-second.log", data["application"]["second"])
        if wait_for_health(second, api_port, data["application"]["second"]) != 200: raise RuntimeError("second health failed")
        data["post_restart_operations"].append({"at": utcnow(), "operation": "health", "method": "GET", "read_only": True})
        data["http"]["post"] = fetch_http_snapshot(base, data["state"]); data["post_restart_operations"].extend({"at": utcnow(), "operation": item, "method": "GET", "read_only": True} for item in ("case", "artifacts", "final_pdf")); data["database"]["post"] = snapshot_database(env); data["filesystem"]["post"] = snapshot_filesystem_stable(data_root); data["verifier"]["post"] = fetch_verifier_snapshot(env, data["state"]); data["post_restart_operations"].extend({"at": utcnow(), "operation": item, "method": "SELECT", "read_only": True} for item in ("database_snapshot", "filesystem_snapshot", "verifiers"))
    except Exception as exc:
        data["error"] = {"type": type(exc).__name__, "message": sanitize_text(exc, secrets_map)}
    finally:
        for process, life in ((second, data["application"]["second"]), (first, data["application"]["first"])):
            try:
                if process is not None and process.poll() is None: stop_uvicorn(process, life)
            except Exception as exc: data["cleanup_errors"].append({"type": type(exc).__name__, "message": sanitize_text(exc, secrets_map)})
        data["postgres_lifecycle"]["cleanup_requested_at"] = utcnow()
        try: data["cleanup"] = cleanup_runtime(project, temporary, evidence, env, commands, secrets_map)
        except Exception as exc: data["cleanup_errors"].append({"type": type(exc).__name__, "message": sanitize_text(exc, secrets_map)})
        data["postgres_lifecycle"]["cleanup_completed_at"] = utcnow()
        for name, value in {"postgres-lifecycle.json": data["postgres_lifecycle"], "application-lifecycle.json": data["application"], "post-restart-operations.json": data["post_restart_operations"], "volume-identity.json": data["volume"], "http-snapshots.json": data["http"], "database-snapshots.json": {**data["database"], "pilot_artifact_binding": data.get("binding", {})}, "filesystem-snapshots.json": data["filesystem"], "verifier-results.json": data["verifier"], "postgres-identity.json": data["postgres"], "commands.log": commands, "cleanup.json": data["cleanup"]}.items(): write_json(evidence / name, sanitize_value(value, secrets_map))
        for name in ("backend-first.log", "backend-second.log"):
            path = evidence / name; path.write_text(sanitize_text(path.read_text(errors="replace") if path.exists() else "", secrets_map))
        first_hits = scan_hygiene(evidence, secrets_map); checks = assertions(data); cleanup = data["cleanup"]; app = data["application"]; checks["cleanup_complete"] = all(item.get("process_exited") is True for item in (app["first"], app["second"])) and data["cleanup_errors"] == [] and cleanup.get("compose_down_exit_code") == 0 and not cleanup.get("containers") and not cleanup.get("volumes") and not cleanup.get("networks") and cleanup.get("temporary_directory_removed") and cleanup.get("evidence_directory_exists"); checks["evidence_hygiene_pass"] = not first_hits
        result = {"status": SUCCESS if not data.get("error") and all(checks.values()) else "FAILED", "assertions": checks, "state": data["state"], "error": data.get("error"), "first_hygiene_hits": first_hits, "final_hygiene_hits": []}; write_json(evidence / "postgres-restart-result.json", sanitize_value(result, secrets_map)); result["final_hygiene_hits"] = scan_hygiene(evidence, secrets_map); result["assertions"]["evidence_hygiene_pass"] = not result["final_hygiene_hits"]
        checks["evidence_pack_complete"] = all((evidence / x).exists() for x in FILES if x != "SHA256SUMS")
        write_json(evidence / "postgres-restart-result.json", sanitize_value(result, secrets_map)); write_sums(evidence)
        sums = (evidence / "SHA256SUMS").read_text().splitlines(); valid_sums = len(sums) == len([p for p in evidence.iterdir() if p.is_file() and p.name != "SHA256SUMS"]) and all(len(line.split("  ", 1)) == 2 and (evidence / line.split("  ", 1)[1]).exists() and __import__("hashlib").sha256((evidence / line.split("  ", 1)[1]).read_bytes()).hexdigest() == line.split("  ", 1)[0] for line in sums)
        checks["sha256sums_complete_and_valid"] = valid_sums; result["assertions"] = checks
        if data.get("error") is None and all(checks.values()) and not result["final_hygiene_hits"]: result["status"] = SUCCESS
        if result["final_hygiene_hits"] or not all(result["assertions"].values()): result["status"] = "FAILED"
        write_json(evidence / "postgres-restart-result.json", sanitize_value(result, secrets_map)); write_sums(evidence); exit_code = 0 if result["status"] == SUCCESS and all(result["assertions"].values()) and data["cleanup_errors"] == [] and not result["final_hygiene_hits"] and checks["evidence_pack_complete"] and checks["sha256sums_complete_and_valid"] else 1
    print(evidence); return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser(); parser.add_argument("--self-test-hygiene", action="store_true"); args = parser.parse_args(); raise SystemExit(0 if run_hygiene_self_test() else 1) if args.self_test_hygiene else SystemExit(main())
