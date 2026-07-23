"""Fail-closed local evidence runner for one R9.1 application restart."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "acceptance"))

from r8_acceptance.runtime import free_port, http  # noqa: E402
from run_r8_acceptance import (  # noqa: E402
    _enrich_states,
    _prepare_customer,
    _seed,
    snapshot_audit,
    snapshot_business_db,
    snapshot_filesystem,
)

COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
CUSTOMER = "R9-RESTART-SYNTHETIC"
SUCCESS = "R9_1_APPLICATION_RESTART_SMOKE_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL"
REQUIRED_FILES = (
    "restart-result.json", "process-lifecycle.json", "http-snapshots.json",
    "database-snapshots.json", "filesystem-snapshots.json", "verifier-results.json",
    "postgres-identity.json", "backend-first.log", "backend-second.log", "commands.log",
    "cleanup.json", "SHA256SUMS",
)


def utcnow() -> str:
    return datetime.now(UTC).isoformat()


def write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, default=str) + "\n")


def sanitize_text(value: Any, secrets_map: dict[str, str]) -> str:
    text = str(value)
    replacements = {
        str(ROOT): "<REPOSITORY_ROOT>", str(Path.home()): "<USER_HOME>",
        sys.executable: "<PROJECT_PYTHON>", secrets_map["database_url"]: "<REDACTED_DATABASE_URL>",
        secrets_map["password"]: "<REDACTED>", secrets_map["temporary_root"]: "<TEMP_DATA_ROOT>",
        secrets_map["authorization"]: "<REDACTED_AUTHORIZATION>",
    }
    for source, replacement in replacements.items():
        if source:
            text = text.replace(source, replacement)
    return text


def sanitize_value(value: Any, secrets_map: dict[str, str]) -> Any:
    if isinstance(value, dict):
        return {str(key): sanitize_value(item, secrets_map) for key, item in value.items()}
    if isinstance(value, list):
        return [sanitize_value(item, secrets_map) for item in value]
    if isinstance(value, tuple):
        return [sanitize_value(item, secrets_map) for item in value]
    return sanitize_text(value, secrets_map) if isinstance(value, str) else value


def scan_hygiene(evidence: Path, secrets_map: dict[str, str]) -> list[dict[str, str]]:
    markers = {
        "generated_password": secrets_map["password"], "database_url": secrets_map["database_url"],
        "repository_root": str(ROOT), "temporary_root": secrets_map["temporary_root"],
        "user_home": str(Path.home()), "authorization": "Authorization",
        "pilot_credentials": secrets_map["authorization"],
    }
    hits: list[dict[str, str]] = []
    for path in evidence.iterdir():
        if not path.is_file() or path.name == "SHA256SUMS":
            continue
        raw = path.read_bytes().decode("utf-8", "replace")
        for marker_name, marker in markers.items():
            if marker and marker in raw:
                hits.append({"file": path.name, "marker": marker_name})
    return hits


def run_hygiene_self_test() -> bool:
    password = "r9-self-test-password"
    temporary = ROOT / "output" / "r9-self-test-temporary"
    database_url = f"postgresql+psycopg://r8:{password}@127.0.0.1:5432/r8"
    authorization = "Authorization: Basic r9-self-test"
    secrets_map = {"password": password, "temporary_root": str(temporary), "database_url": database_url, "authorization": authorization}
    raw = f"{password}\n{database_url}\n{ROOT}\n{temporary}\n{Path.home()}\n{authorization}"
    scratch = Path(tempfile.mkdtemp(prefix="r9-hygiene-"))
    try:
        (scratch / "raw.txt").write_text(raw)
        detects_raw = len(scan_hygiene(scratch, secrets_map)) >= 6
        (scratch / "raw.txt").write_text(sanitize_text(raw, secrets_map))
        detects_clean = scan_hygiene(scratch, secrets_map) == []
        return detects_raw and detects_clean
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


def run_command(args: list[str], env: dict[str, str], commands: list[dict[str, Any]], secrets_map: dict[str, str], check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
    commands.append(sanitize_value({"at": utcnow(), "command": " ".join(args), "exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr}, secrets_map))
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed ({result.returncode}): {result.stderr or result.stdout}")
    return result


def start_uvicorn(env: dict[str, str], port: int, log: Path, lifecycle: dict[str, Any]) -> subprocess.Popen[str]:
    lifecycle["start_requested_at"] = utcnow()
    handle = log.open("a", encoding="utf-8")
    process = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env, stdout=handle, stderr=subprocess.STDOUT, text=True, preexec_fn=os.setsid)
    handle.close()
    lifecycle["process_started_at"] = utcnow()
    lifecycle["pid"] = process.pid
    return process


def health_status(port: int) -> int | None:
    try:
        return http("GET", f"http://127.0.0.1:{port}/health", username="", password="")[0]
    except OSError:
        return None


def wait_for_health(process: subprocess.Popen[str], port: int, lifecycle: dict[str, Any]) -> int | None:
    deadline = time.monotonic() + 30
    status: int | None = None
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError("uvicorn exited before /health became available")
        status = health_status(port)
        if status == 200:
            break
        time.sleep(0.2)
    lifecycle["health_checked_at"] = utcnow()
    lifecycle["health_status"] = status
    return status


def stop_uvicorn(process: subprocess.Popen[str] | None, lifecycle: dict[str, Any]) -> None:
    if process is None:
        return
    lifecycle["stop_requested_at"] = utcnow()
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGTERM)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)
    lifecycle["exited_at"] = utcnow()
    lifecycle["return_code"] = process.returncode
    lifecycle["termination_method"] = {-15: "SIGTERM", -9: "SIGKILL"}.get(process.returncode, "UNEXPECTED")
    lifecycle["process_exited"] = process.poll() is not None


def fetch_case_snapshot(base: str, state: dict[str, Any]) -> tuple[int | None, dict[str, Any]]:
    status, body, _ = http("GET", f"{base}/cases/{state['case_id']}", username="", password="")
    return status, json.loads(body)


def fetch_artifact_snapshot(base: str, state: dict[str, Any]) -> tuple[int | None, list[dict[str, Any]]]:
    status, body, _ = http("GET", f"{base}/cases/{state['case_id']}/runs/{state['run_id']}/artifacts", username="", password="")
    return status, json.loads(body)


def fetch_pdf_snapshot(base: str, state: dict[str, Any]) -> tuple[int | None, bytes]:
    return http("GET", f"{base}/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf", username="", password="")[:2]


def fetch_http_snapshot(base: str, state: dict[str, Any]) -> dict[str, Any]:
    case_status, case = fetch_case_snapshot(base, state)
    artifacts_status, artifacts = fetch_artifact_snapshot(base, state)
    pdf_status, pdf_bytes = fetch_pdf_snapshot(base, state)
    return {"case_status": case_status, "case": case, "artifacts_status": artifacts_status, "artifacts": artifacts, "pdf_status": pdf_status, "pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(), "pdf_byte_size": len(pdf_bytes)}


def fetch_db_artifact_binding(env: dict[str, str], state: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from src.modules.customer_pilot.models import PilotArtifact
    with Session(create_engine(env["AI_CORP_DATABASE_URL"])) as session:
        artifact = session.scalar(select(PilotArtifact).where(PilotArtifact.run_id == state["run_id"], PilotArtifact.artifact_type == "final_pdf"))
        if artifact is None:
            raise RuntimeError("PilotArtifact final_pdf is absent")
        fields = ("id", "run_id", "run_result_id", "artifact_type", "artifact_key", "report_model_hash", "renderer_version", "pdf_sha256", "byte_size", "status", "immutable_at", "pdf_relative_path")
        return {field: getattr(artifact, field) for field in fields}


def fetch_verifier_snapshot(env: dict[str, str], state: dict[str, Any]) -> dict[str, Any]:
    code = """import json,os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotReview,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
from src.modules.customer_pilot.artifacts import verified_pilot_artifact,verify_review_artifact_binding
s=json.loads(os.environ['R9_STATE']); e=create_engine(os.environ['AI_CORP_DATABASE_URL'])
with Session(e) as x:
 r=x.get(PilotRunResult,s['run_result_id']);a=x.get(PilotArtifact,s['artifact_id']);v=x.get(PilotReview,s['review_id']);c=x.get(ProcurementCase,s['case_id']);run=x.get(TenderAnalysisRun,s['run_id'])
 b=verify_run_snapshot_binding(run=run,case=c,binding=r);aa=verified_pilot_artifact(run,c,r,a);verify_review_artifact_binding(review=v,run=run,case=c,result=r,artifact=a,verified_artifact=aa)
 print(json.dumps({'canonical':'PASS','artifact':'PASS','review':'PASS','canonical_hash':b.canonical_report_file_sha256,'pdf_sha256':aa.pdf_sha256}))"""
    verifier_env = env.copy()
    verifier_env["R9_STATE"] = json.dumps(state)
    result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=verifier_env, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    return json.loads(result.stdout)


def snapshot_postgres_identity(project: str) -> dict[str, Any]:
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    container = subprocess.run(compose + ["ps", "-q", "postgres"], cwd=ROOT, text=True, capture_output=True, check=True).stdout.strip()
    inspect = subprocess.run(["docker", "inspect", container, "--format", "{{.Id}}|{{.State.StartedAt}}|{{.RestartCount}}"], text=True, capture_output=True, check=True).stdout.strip().split("|")
    return {"container_id": inspect[0], "started_at": inspect[1], "restart_count": int(inspect[2])}


def snapshot_database(env: dict[str, str]) -> dict[str, Any]:
    return {"business": snapshot_business_db(env), "audit_count": snapshot_audit(env)}


def cleanup_runtime(project: str, temp_root: Path, evidence: Path, env: dict[str, str], commands: list[dict[str, Any]], secrets_map: dict[str, str]) -> dict[str, Any]:
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    down = run_command(compose + ["down", "-v", "--remove-orphans"], env, commands, secrets_map, check=False)
    def ids(command: list[str]) -> list[str]:
        return subprocess.run(command, text=True, capture_output=True).stdout.strip().splitlines()
    resources = {"containers": ids(["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"]), "volumes": ids(["docker", "volume", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"]), "networks": ids(["docker", "network", "ls", "-q", "--filter", f"label=com.docker.compose.project={project}"])}
    shutil.rmtree(temp_root, ignore_errors=True)
    return {"compose_down_exit_code": down.returncode, **resources, "temporary_directory_removed": not temp_root.exists(), "evidence_directory_exists": evidence.exists()}


def calculate_assertions(data: dict[str, Any]) -> dict[str, bool]:
    pre, post = data.get("http", {}).get("pre", {}), data.get("http", {}).get("post", {})
    first, second = data["lifecycle"]["first"], data["lifecycle"]["second"]
    binding = data.get("binding", {})
    postgres_pre = data.get("postgres", {}).get("pre", {})
    postgres_post = data.get("postgres", {}).get("post", {})
    expected_artifact_fields = ("id", "artifact_type", "artifact_key", "report_model_hash", "renderer_version", "pdf_sha256", "byte_size", "immutable_at", "status")
    pre_artifacts, post_artifacts = pre.get("artifacts", []), post.get("artifacts", [])
    first_exit = datetime.fromisoformat(first["exited_at"]) if first.get("exited_at") else None
    second_start = datetime.fromisoformat(second["start_requested_at"]) if second.get("start_requested_at") else None
    case_keys = ("id", "customer_id", "project_id", "artifact_key")
    case_identity = all(pre.get("case", {}).get(key) == post.get("case", {}).get(key) for key in case_keys)
    pre_runs = pre.get("case", {}).get("runs", [])
    post_runs = post.get("case", {}).get("runs", [])
    run_identity = (
        len(pre_runs) == len(post_runs) == 1
        and pre_runs[0].get("id") == post_runs[0].get("id") == data["state"].get("run_id")
        and pre_runs[0].get("status") == post_runs[0].get("status") == "completed"
    )
    artifact_identity = len(pre_artifacts) == len(post_artifacts) == 1 and all(pre_artifacts[0].get(key) == post_artifacts[0].get(key) for key in expected_artifact_fields)
    def normalized(value: Any) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)
    db = data.get("database", {})
    return {
        "first_health_200": first.get("health_status") == 200,
        "second_health_200": second.get("health_status") == 200,
        "first_health_unavailable_after_stop": data.get("first_health_after_stop") is None,
        "different_pids": first.get("pid") is not None and first.get("pid") != second.get("pid"),
        "first_exited_before_second_started": first_exit is not None and second_start is not None and first_exit <= second_start,
        "both_return_codes_recorded": all(item.get("return_code") is not None for item in (first, second)),
        "process_termination_expected": all(item.get("termination_method") in {"SIGTERM", "SIGKILL"} for item in (first, second)),
        "postgres_container_id_unchanged": bool(postgres_pre) and postgres_pre.get("container_id") == postgres_post.get("container_id"),
        "postgres_started_at_unchanged": bool(postgres_pre) and postgres_pre.get("started_at") == postgres_post.get("started_at"),
        "postgres_restart_count_unchanged": bool(postgres_pre) and postgres_pre.get("restart_count") == postgres_post.get("restart_count"),
        "alembic_revision_unchanged": data.get("revision", {}).get("pre") == data.get("revision", {}).get("post") == "096_add_r8_canonical_snapshot_binding",
        "db_snapshots_equal": db.get("pre") == db.get("post"), "filesystem_snapshots_equal": data["filesystem"].get("pre") == data["filesystem"].get("post"),
        "canonical_verifier_pass_pre_post": data.get("verifier", {}).get("pre", {}).get("canonical") == data.get("verifier", {}).get("post", {}).get("canonical") == "PASS",
        "artifact_verifier_pass_pre_post": data.get("verifier", {}).get("pre", {}).get("artifact") == data.get("verifier", {}).get("post", {}).get("artifact") == "PASS",
        "review_verifier_pass_pre_post": data.get("verifier", {}).get("pre", {}).get("review") == data.get("verifier", {}).get("post", {}).get("review") == "PASS",
        "case_http_identity_preserved": pre.get("case_status") == post.get("case_status") == 200 and case_identity and run_identity and pre.get("case", {}).get("status") == post.get("case", {}).get("status") == "delivered",
        "lifecycle_http_preserved": pre.get("case", {}).get("status") == post.get("case", {}).get("status") == "delivered",
        "artifact_http_identity_preserved": pre.get("artifacts_status") == post.get("artifacts_status") == 200 and artifact_identity and all(normalized(post_artifacts[0].get(key)) == normalized(binding.get(key)) for key in expected_artifact_fields),
        "pdf_bytes_equal": pre.get("pdf_sha256") == post.get("pdf_sha256") and pre.get("pdf_byte_size") == post.get("pdf_byte_size"),
        "pdf_hash_matches_db": pre.get("pdf_sha256") == post.get("pdf_sha256") == binding.get("pdf_sha256"),
        "pdf_size_matches_db": pre.get("pdf_byte_size") == post.get("pdf_byte_size") == binding.get("byte_size"),
        "one_run_result": db.get("pre", {}).get("business", {}).get("PilotRunResult", {}).get("count") == 1,
        "one_final_artifact": db.get("pre", {}).get("business", {}).get("PilotArtifact", {}).get("count") == 1,
        "one_review": db.get("pre", {}).get("business", {}).get("PilotReview", {}).get("count") == 1,
        "no_canonical_partials": not any(".analysis.partial." in path for path in data["filesystem"].get("pre", {})),
        "no_artifact_partials": not any(".artifact." in path and ".partial." in path for path in data["filesystem"].get("pre", {})),
        "audit_count_unchanged": db.get("pre", {}).get("audit_count") == db.get("post", {}).get("audit_count"),
        "cleanup_complete": False, "evidence_hygiene_pass": False,
    }


def write_evidence_files(evidence: Path, data: dict[str, Any], commands: list[dict[str, Any],], secrets_map: dict[str, str]) -> None:
    write_json(evidence / "process-lifecycle.json", sanitize_value(data["lifecycle"], secrets_map))
    write_json(evidence / "http-snapshots.json", sanitize_value(data.get("http", {}), secrets_map))
    database_evidence = {**data.get("database", {}), "pilot_artifact_binding": data.get("binding", {})}
    write_json(evidence / "database-snapshots.json", sanitize_value(database_evidence, secrets_map))
    write_json(evidence / "filesystem-snapshots.json", sanitize_value(data.get("filesystem", {}), secrets_map))
    write_json(evidence / "verifier-results.json", sanitize_value(data.get("verifier", {}), secrets_map))
    write_json(evidence / "postgres-identity.json", sanitize_value(data.get("postgres", {}), secrets_map))
    write_json(evidence / "commands.log", commands)
    write_json(evidence / "cleanup.json", sanitize_value(data.get("cleanup", {}), secrets_map))
    for name in ("backend-first.log", "backend-second.log"):
        path = evidence / name
        path.write_text(sanitize_text(path.read_text(errors="replace") if path.exists() else "", secrets_map))


def write_sums(evidence: Path) -> None:
    entries = []
    for path in sorted(evidence.iterdir()):
        if path.is_file() and path.name != "SHA256SUMS":
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (evidence / "SHA256SUMS").write_text("\n".join(entries) + "\n")


def revision(env: dict[str, str], commands: list[dict[str, Any]], secrets_map: dict[str, str]) -> str:
    code = "from sqlalchemy import create_engine,text;import os;print(create_engine(os.environ['AI_CORP_DATABASE_URL']).connect().execute(text('select version_num from alembic_version')).scalar_one())"
    return run_command([sys.executable, "-c", code], env, commands, secrets_map).stdout.strip()


def finalize_result(evidence: Path, data: dict[str, Any], commands: list[dict[str, Any]], secrets_map: dict[str, str]) -> tuple[dict[str, Any], int]:
    write_evidence_files(evidence, data, commands, secrets_map)
    first_hits = scan_hygiene(evidence, secrets_map)
    assertions = calculate_assertions(data)
    cleanup = data.get("cleanup", {})
    assertions["cleanup_complete"] = bool(cleanup.get("compose_down_exit_code") == 0 and not cleanup.get("containers") and not cleanup.get("volumes") and not cleanup.get("networks") and cleanup.get("temporary_directory_removed") and cleanup.get("evidence_directory_exists"))
    assertions["evidence_hygiene_pass"] = first_hits == []
    result = {"status": "FAILED", "assertions": assertions, "state": data.get("state", {}), "error": data.get("error"), "cleanup_errors": data.get("cleanup_errors", []), "first_hygiene_hits": first_hits, "final_hygiene_hits": []}
    if data.get("error") is None and all(assertions.values()):
        result["status"] = SUCCESS
    write_json(evidence / "restart-result.json", sanitize_value(result, secrets_map))
    final_hits = scan_hygiene(evidence, secrets_map)
    result["final_hygiene_hits"] = final_hits
    result["assertions"]["evidence_hygiene_pass"] = final_hits == []
    if final_hits or not all(result["assertions"].values()):
        result["status"] = "FAILED"
    write_json(evidence / "restart-result.json", sanitize_value(result, secrets_map))
    write_sums(evidence)
    all_files = all((evidence / name).exists() for name in REQUIRED_FILES)
    exit_code = 0 if result["status"] == SUCCESS and all(result["assertions"].values()) and final_hits == [] and result["assertions"]["cleanup_complete"] and all_files else 1
    return result, exit_code


def main() -> int:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "output" / f"r9-application-restart-{stamp}"
    evidence.mkdir(parents=True)
    temporary_root = Path(tempfile.mkdtemp(prefix="r9-restart-", dir=ROOT / "output"))
    data_root = temporary_root / "data"
    data_root.mkdir()
    postgres_port, api_port = free_port(), free_port()
    password = "r9-" + secrets.token_urlsafe(20)
    project = "r9restart" + secrets.token_hex(5)
    database_url = f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{postgres_port}/r8_acceptance"
    secrets_map = {"password": password, "temporary_root": str(temporary_root), "database_url": database_url, "authorization": "Authorization: Basic Og=="}
    env = os.environ.copy()
    env.update({"R8_POSTGRES_PASSWORD": password, "R8_POSTGRES_PORT": str(postgres_port), "AI_CORP_DATABASE_URL": database_url, "AI_CORP_ARVECTUM_DATA_DIR": str(data_root), "AI_CORP_PILOT_AUTH_ENABLED": "false", "AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED": "false"})
    commands: list[dict[str, Any]] = []
    data: dict[str, Any] = {"state": {}, "lifecycle": {"first": {}, "second": {}}, "http": {}, "database": {}, "filesystem": {}, "verifier": {}, "postgres": {}, "cleanup": {}, "cleanup_errors": []}
    first_runtime: Any = None
    second_runtime: Any = None
    first_process: subprocess.Popen[str] | None = None
    second_process: subprocess.Popen[str] | None = None
    try:
        compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
        run_command(compose + ["up", "-d", "--wait"], env, commands, secrets_map)
        run_command([sys.executable, "-m", "alembic", "upgrade", "096_add_r8_canonical_snapshot_binding"], env, commands, secrets_map)
        data["revision"] = {"pre": revision(env, commands, secrets_map)}
        _seed(env)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session
        from src.modules.customer_registry.models import CustomerProfile
        with Session(create_engine(database_url)) as session:
            session.add(CustomerProfile(customer_id=CUSTOMER, legal_name="R9 synthetic customer", customer_status="prospect"))
            session.commit()
        first_process = start_uvicorn(env, api_port, evidence / "backend-first.log", data["lifecycle"]["first"])
        first_runtime = first_process
        if wait_for_health(first_process, api_port, data["lifecycle"]["first"]) != 200:
            raise RuntimeError("first /health was not 200")
        base = f"http://127.0.0.1:{api_port}/api/operator/pilot/customers/{CUSTOMER}"
        data["state"] = _prepare_customer("http://127.0.0.1:%s/api/operator/pilot/customers/{customer}" % api_port, "", "", CUSTOMER)
        _enrich_states(env, [data["state"]])
        data["http"]["pre"] = fetch_http_snapshot(base, data["state"])
        data["database"]["pre"] = snapshot_database(env)
        data["filesystem"]["pre"] = snapshot_filesystem(data_root)
        data["verifier"]["pre"] = fetch_verifier_snapshot(env, data["state"])
        data["binding"] = fetch_db_artifact_binding(env, data["state"])
        data["postgres"]["pre"] = snapshot_postgres_identity(project)
        stop_uvicorn(first_process, data["lifecycle"]["first"])
        data["first_health_after_stop"] = health_status(api_port)
        if data["first_health_after_stop"] is not None:
            raise RuntimeError("/health remained available after first uvicorn stop")
        second_process = start_uvicorn(env, api_port, evidence / "backend-second.log", data["lifecycle"]["second"])
        second_runtime = second_process
        if wait_for_health(second_process, api_port, data["lifecycle"]["second"]) != 200:
            raise RuntimeError("second /health was not 200")
        data["http"]["post"] = fetch_http_snapshot(base, data["state"])
        data["database"]["post"] = snapshot_database(env)
        data["filesystem"]["post"] = snapshot_filesystem(data_root)
        data["verifier"]["post"] = fetch_verifier_snapshot(env, data["state"])
        data["postgres"]["post"] = snapshot_postgres_identity(project)
        data["revision"]["post"] = revision(env, commands, secrets_map)
    except Exception as exc:
        data["error"] = {"type": type(exc).__name__, "message": sanitize_text(exc, secrets_map)}
    finally:
        for process, lifecycle in ((second_process, data["lifecycle"]["second"]), (first_process, data["lifecycle"]["first"])):
            try:
                if process is not None and process.poll() is None:
                    stop_uvicorn(process, lifecycle)
            except Exception as exc:
                data["cleanup_errors"].append({"type": type(exc).__name__, "message": sanitize_text(exc, secrets_map)})
        try:
            data["cleanup"] = cleanup_runtime(project, temporary_root, evidence, env, commands, secrets_map)
        except Exception as exc:
            data["cleanup_errors"].append({"type": type(exc).__name__, "message": sanitize_text(exc, secrets_map)})
        result, exit_code = finalize_result(evidence, data, commands, secrets_map)
    print(evidence)
    return exit_code


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test-hygiene", action="store_true")
    arguments = parser.parse_args()
    raise SystemExit(0 if run_hygiene_self_test() else 1) if arguments.self_test_hygiene else SystemExit(main())
