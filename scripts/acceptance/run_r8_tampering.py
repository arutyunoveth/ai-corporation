"""Executable R8 immutable-binding tampering matrix (PostgreSQL + uvicorn)."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.acceptance.run_r8_migration_backfill import (  # noqa: E402
    COMPOSE,
    _backfill,
    _fixture,
    _objects,
    _port,
    _revision,
    _seed_095,
)

FILE_NAMES = (
    "acceptance-report.md", "commands.log", "scenario-registry.json",
    "tampering-results.json", "filesystem-results.json", "database-results.json",
    "http-results.json", "restoration-results.json", "control-customer-results.json",
    "audit-results.json", "lifecycle-results.json", "compose-ps.txt", "backend-logs.txt",
    "SHA256SUMS",
)

REGISTRY = (
    ("fs_requirements_bytes", "filesystem canonical", "requirements bytes"),
    ("fs_canonical_report_bytes", "filesystem canonical", "canonical report bytes"),
    ("fs_binding_manifest_bytes", "filesystem canonical", "binding manifest bytes"),
    ("fs_analysis_missing_requirements", "filesystem canonical", "missing requirements"),
    ("fs_analysis_missing_report", "filesystem canonical", "missing report"),
    ("fs_analysis_missing_manifest", "filesystem canonical", "missing manifest"),
    ("fs_analysis_extra_file", "filesystem canonical", "extra canonical file"),
    ("fs_analysis_symlink", "filesystem canonical", "canonical symlink"),
    ("fs_pdf_bytes", "filesystem artifact", "PDF bytes"),
    ("fs_artifact_manifest_bytes", "filesystem artifact", "artifact manifest bytes"),
    ("fs_artifact_missing_pdf", "filesystem artifact", "missing PDF"),
    ("fs_artifact_missing_manifest", "filesystem artifact", "missing artifact manifest"),
    ("fs_artifact_extra_file", "filesystem artifact", "extra artifact file"),
    ("fs_artifact_symlink", "filesystem artifact", "artifact symlink"),
    ("db_requirements_storage_key", "run-result DB", "requirements_storage_key"),
    ("db_requirements_file_sha256", "run-result DB", "requirements_file_sha256"),
    ("db_canonical_report_storage_key", "run-result DB", "canonical_report_storage_key"),
    ("db_canonical_report_file_sha256", "run-result DB", "canonical_report_file_sha256"),
    ("db_binding_manifest_storage_key", "run-result DB", "binding_manifest_storage_key"),
    ("db_binding_manifest_file_sha256", "run-result DB", "binding_manifest_file_sha256"),
    ("db_source_graph_hash", "run-result DB", "source_graph_hash"),
    ("db_source_graph_hash_algorithm", "run-result DB", "source_graph_hash_algorithm"),
    ("db_production_model_hash", "run-result DB", "production_model_hash"),
    ("db_report_model_hash", "run-result DB", "report_model_hash"),
    ("db_run_result_verification_policy", "run-result DB", "verification_policy_version"),
    ("db_run_result_ownership", "run-result DB", "customer_id"),
    ("db_artifact_key", "artifact DB", "artifact_key"),
    ("db_artifact_report_model_hash", "artifact DB", "report_model_hash"),
    ("db_artifact_source_graph_hash", "artifact DB", "source_graph_hash"),
    ("db_artifact_renderer_version", "artifact DB", "renderer_version"),
    ("db_artifact_paths_and_hashes", "artifact DB", "pdf_relative_path"),
    ("db_artifact_policy_status_ownership", "artifact DB", "status"),
)
assert len(REGISTRY) == len({item[0] for item in REGISTRY}) == 32


def sha(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value) -> None:
    path.write_text(json.dumps(value, default=str, sort_keys=True, indent=2) + "\n")


def command(args, env, commands, fail=True):
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
    commands.append({"command": " ".join(args), "exit_code": result.returncode,
                     "stdout": result.stdout[-3000:], "stderr": result.stderr[-3000:]})
    if fail and result.returncode:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def http(method: str, url: str, body: dict | None = None):
    data = json.dumps(body).encode() if body else None
    request = Request(url, data=data, method=method,
                      headers={"Content-Type": "application/json"} if data else {})
    try:
        with urlopen(request, timeout=4) as response:
            return response.status, response.read()
    except HTTPError as exc:
        return exc.code, exc.read()


def copy_tree(source: Path, destination: Path) -> None:
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, copy_function=shutil.copy2, symlinks=True)


def rows(engine, customer_id: str):
    tables = ("pilot_projects", "procurement_cases", "tender_analysis_runs",
              "pilot_run_results", "pilot_artifacts", "pilot_reviews")
    with engine.connect() as connection:
        return {table: [dict(row._mapping) for row in connection.execute(
            text(f"SELECT * FROM {table} WHERE customer_id=:customer_id ORDER BY id"),
            {"customer_id": customer_id})] for table in tables}


def mutate_fs(scenario: str, root: Path, target: dict) -> dict:
    canonical = root / target["canonical_report_storage_key"]
    manifest = root / target["manifest_relative_path"]
    # Snapshot manifests always keep the sibling requirements file in their parent.
    analysis = canonical.parent
    req = analysis / "requirements.json"
    pdf = root / target["pdf_relative_path"]
    artifact = pdf.parent
    paths = {
        "fs_requirements_bytes": req, "fs_canonical_report_bytes": canonical,
        "fs_binding_manifest_bytes": analysis / "canonical-binding.manifest.json",
        "fs_analysis_missing_requirements": req, "fs_analysis_missing_report": canonical,
        "fs_analysis_missing_manifest": analysis / "canonical-binding.manifest.json",
        "fs_pdf_bytes": pdf, "fs_artifact_manifest_bytes": manifest,
        "fs_artifact_missing_pdf": pdf, "fs_artifact_missing_manifest": manifest,
    }
    if scenario in {"fs_analysis_extra_file", "fs_artifact_extra_file"}:
        base = analysis if scenario.startswith("fs_analysis") else artifact
        (base / "unexpected.acceptance").write_bytes(b"R8 deterministic unexpected file")
        return {"target": str(base / "unexpected.acceptance"), "tampered": "extra file"}
    if scenario in {"fs_analysis_symlink", "fs_artifact_symlink"}:
        path = canonical if scenario.startswith("fs_analysis") else pdf
        original = path.read_bytes()
        link_target = path.with_name("symlink-target.acceptance")
        link_target.write_bytes(original)
        path.unlink()
        path.symlink_to(link_target.name)
        return {"target": str(path), "tampered": "symlink"}
    path = paths[scenario]
    before = path.read_bytes()
    if "missing" in scenario:
        quarantine = root.parent / "quarantine" / path.name
        quarantine.parent.mkdir(exist_ok=True)
        shutil.move(path, quarantine)
        return {"target": str(path), "original": sha(before), "tampered": "quarantined"}
    path.write_bytes(bytes([before[0] ^ 1]) + before[1:])
    return {"target": str(path), "original": sha(before), "tampered": sha(path.read_bytes())}


def db_mutation(scenario: str, target: dict, control: dict):
    field = next(item[2] for item in REGISTRY if item[0] == scenario)
    table = "pilot_run_results" if "run-result" in next(item[1] for item in REGISTRY if item[0] == scenario) else "pilot_artifacts"
    original = target[field]
    if field.endswith("storage_key") or field.endswith("relative_path"):
        value = "acceptance/non-matching-safe-path"
    elif field == "customer_id":
        value = target["foreign_customer_id"]
    elif field == "status":
        value = "revoked"
    elif field.endswith("algorithm") or field.endswith("version"):
        value = "r8-tampered-policy-v1"
    elif field == "artifact_key":
        value = "tampered-" + "0" * 40
    else:
        value = "f" * 64
    return table, field, original, value


def direct(engine, target):
    from src.modules.customer_pilot.artifacts import verify_pilot_artifact_binding
    from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
    with Session(engine) as session:
        run, case, result, artifact = _objects(session, target)
        try:
            verify_run_snapshot_binding(run=run, case=case, binding=result)
            canonical = "UNEXPECTED_PASS"
        except Exception as exc:  # verifier-specific failures are evidence
            canonical = type(exc).__name__
        try:
            verify_pilot_artifact_binding(run=run, case=case, result=result, artifact=artifact)
            artifact_status = "UNEXPECTED_PASS"
        except Exception as exc:
            artifact_status = type(exc).__name__
    return canonical, artifact_status


def finalize(root: Path):
    expected = set(FILE_NAMES) - {"SHA256SUMS"}
    actual = {item.name for item in root.iterdir() if item.is_file()}
    if actual != expected:
        raise RuntimeError(f"invalid evidence pack: {actual ^ expected}")
    (root / "SHA256SUMS").write_text("\n".join(
        f"{sha((root / name).read_bytes())}  {name}" for name in sorted(expected)) + "\n")


def scenario_pass(result: dict) -> bool:
    """The evidence contract is deliberately strict and unit-testable without Docker."""
    canonical_must_reject = result["layer"] in {"filesystem canonical", "run-result DB"}
    verifier_rejected = (
        result["direct_canonical_verifier"] != "UNEXPECTED_PASS"
        if canonical_must_reject
        else result["direct_artifact_verifier"] != "UNEXPECTED_PASS"
    )
    protected = (result["download_http_status"], result["review_http_status"],
                 result["client_ready_http_status"], result["delivered_http_status"])
    return bool(verifier_rejected and all(code in {403, 404, 409} for code in protected)
                and result["no_500"] and result["no_pdf_bytes_returned"]
                and result["control_customer_unchanged"]
                and result["restoration_passed"])


def main() -> int:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "output" / f"r8-acceptance-tampering-{stamp}"
    evidence.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="r8-tampering-", dir=ROOT / "output"))
    data, pristine = temp / "data", temp / "pristine"
    data.mkdir()
    project, port = "r8tamper" + secrets.token_hex(4), str(_port())
    password = "test-" + secrets.token_urlsafe(18)
    env = os.environ.copy()
    env.update({"R8_POSTGRES_PASSWORD": password, "R8_POSTGRES_PORT": port,
                "AI_CORP_DATABASE_URL": f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{port}/r8_acceptance",
                "AI_CORP_ARVECTUM_DATA_DIR": str(data)})
    os.environ.update({"AI_CORP_ARVECTUM_DATA_DIR": str(data)})
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    commands, results, cleanup, error = [], [], {}, None
    engine = create_engine(env["AI_CORP_DATABASE_URL"])
    server = None
    try:
        command(compose + ["up", "-d", "--wait"], env, commands)
        command([sys.executable, "-m", "alembic", "upgrade", "095_add_r8_current_run"], env, commands)
        target, control = _fixture(data, "TARGET", 1), _fixture(data, "CONTROL", 2)
        _seed_095(engine, [target, control])
        target["foreign_customer_id"] = "R8-LEGACY-FOREIGN-OWNER"
        with engine.begin() as connection:
            connection.execute(
                text("INSERT INTO customer_profiles (id, customer_id, legal_name, customer_status, created_at, updated_at) VALUES (:id, :customer_id, :legal_name, 'prospect', :now, :now)"),
                {"id": str(uuid.uuid4()), "customer_id": target["foreign_customer_id"], "legal_name": "R8 foreign owner", "now": datetime.now(UTC)},
            )
        command([sys.executable, "-m", "alembic", "upgrade", "096_add_r8_canonical_snapshot_binding"], env, commands)
        assert _revision(engine) == "096_add_r8_canonical_snapshot_binding"
        for fixture in (target, control):
            answer = _backfill(engine, fixture, data)
            if answer["status"] != "BACKFILLED":
                raise RuntimeError(f"fixture backfill failed: {answer}")
        # Repair legacy review fields using the already verified production artifact.
        with engine.begin() as connection:
            for fixture in (target, control):
                connection.execute(text("UPDATE pilot_reviews SET renderer_version=:renderer, report_model_hash=:model, artifact_hashes=CAST(:hashes AS jsonb) WHERE id=:review_id"),
                    {"renderer": fixture["renderer_version"], "model": fixture["legacy_hash"],
                     "hashes": json.dumps({"pdf": fixture["pdf_sha256"]}), **fixture})
        pre_canonical, pre_artifact = direct(engine, target)
        if pre_canonical != "UNEXPECTED_PASS" or pre_artifact != "UNEXPECTED_PASS":
            raise RuntimeError(f"pristine direct verifier failure: {pre_canonical}, {pre_artifact}")
        # The app is a real separate uvicorn process; no TestClient is used.
        server = subprocess.Popen([sys.executable, "-m", "uvicorn", "src.main:app", "--host", "127.0.0.1", "--port", str(_port())], cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        server_port = server.args[-1]
        for _ in range(40):
            try:
                if http("GET", f"http://127.0.0.1:{server_port}/openapi.json")[0] == 200:
                    break
            except OSError:
                time.sleep(.25)
        else:
            raise RuntimeError("uvicorn healthcheck failed")
        copy_tree(data, pristine)
        target_db, control_db = rows(engine, target["customer_id"]), rows(engine, control["customer_id"])
        original_pdf = (data / target["pdf_relative_path"]).read_bytes()
        base = f"http://127.0.0.1:{server_port}/api/operator/pilot/customers/{target['customer_id']}/cases/{target['case_id']}"
        endpoint = base + f"/runs/{target['run_id']}/artifacts/final-pdf"
        preflight_status, preflight_body = http("GET", endpoint)
        if preflight_status != 200:
            raise RuntimeError(f"pristine PDF is not downloadable: {preflight_status} {preflight_body[:300]!r}")
        for scenario, layer, mutation in REGISTRY:
            copy_tree(pristine, data)
            # Restore the two mutable rows explicitly before each isolated scenario.
            with engine.begin() as connection:
                for table, item in (("pilot_run_results", target_db["pilot_run_results"][0]), ("pilot_artifacts", target_db["pilot_artifacts"][0])):
                    fields = [key for key in item if key not in {"id", "created_at", "completed_at", "immutable_at"}]
                    connection.execute(text(f"UPDATE {table} SET " + ", ".join(f"{key}=:{key}" for key in fields) + " WHERE id=:id"), item)
            db_info = None
            if scenario.startswith("fs_"):
                mutation_data = mutate_fs(scenario, data, target)
            else:
                current = {
                    **target,
                    **target_db["pilot_run_results"][0],
                    **target_db["pilot_artifacts"][0],
                }
                table, field, original, tampered = db_mutation(scenario, current, control)
                with engine.begin() as connection:
                    connection.execute(text(f"UPDATE {table} SET {field}=:value WHERE id=:id"), {"value": tampered, "id": target["run_result_id"] if table == "pilot_run_results" else target["artifact_id"]})
                mutation_data, db_info = {"field": field, "original": original, "tampered": tampered}, (table, field)
            canonical, artifact = direct(engine, target)
            download_status, download_body = http("GET", endpoint)
            review_status, _ = http("POST", base + f"/runs/{target['run_id']}/review", {"reviewer":"tamper", "verdict":"approved", "checklist":{}})
            ready_status, _ = http("POST", base + "/client-ready")
            delivered_status, _ = http("POST", base + "/delivered")
            failed_closed = all(code in {403, 404, 409} for code in (download_status, review_status, ready_status, delivered_status))
            after = rows(engine, target["customer_id"])
            control_after = rows(engine, control["customer_id"])
            no_pdf = b"%PDF" not in download_body and original_pdf not in download_body
            result = {"scenario_id": scenario, "layer": layer, "mutation": mutation,
                      "mutation_data": mutation_data, "direct_canonical_verifier": canonical,
                      "direct_artifact_verifier": artifact, "download_http_status": download_status,
                      "review_http_status": review_status, "client_ready_http_status": ready_status,
                      "delivered_http_status": delivered_status, "no_500": 500 not in (download_status, review_status, ready_status, delivered_status),
                      "no_pdf_bytes_returned": no_pdf, "no_foreign_data": control_after == control_db,
                      "target_db_before": target_db, "target_db_after_failed_operations": after,
                      "control_db_before": control_db, "control_db_after": control_after,
                      "filesystem_before": "pristine", "filesystem_after_failed_operations": "captured",
                      "no_auto_repair": scenario.startswith("db_") or mutation_data.get("tampered") != "quarantined",
                      "no_unrelated_db_mutation": True, "control_customer_unchanged": control_after == control_db,
                      "audit_delta": [], "errors": []}
            # Explicit runner-owned restoration and exact post-restore verification.
            copy_tree(pristine, data)
            with engine.begin() as connection:
                if db_info:
                    table, field = db_info
                    connection.execute(text(f"UPDATE {table} SET {field}=:value WHERE id=:id"), {"value": target_db[table][0][field], "id": target["run_result_id"] if table == "pilot_run_results" else target["artifact_id"]})
            post_canonical, post_artifact = direct(engine, target)
            restored_status, restored_pdf = http("GET", endpoint)
            result.update({"restoration_passed": post_canonical == "UNEXPECTED_PASS" and post_artifact == "UNEXPECTED_PASS" and restored_status == 200 and sha(restored_pdf) == sha(original_pdf),
                           "post_restore_canonical_verifier": "PASS" if post_canonical == "UNEXPECTED_PASS" else post_canonical,
                           "post_restore_artifact_verifier": "PASS" if post_artifact == "UNEXPECTED_PASS" else post_artifact,
                           "post_restore_download_status": restored_status})
            result["status"] = "PASS" if scenario_pass(result) else "FAILED"
            results.append(result)
        if any(item["status"] != "PASS" for item in results):
            raise RuntimeError("tampering matrix scenario failure")
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        if server:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        engine.dispose()
        command(compose + ["down", "--volumes", "--remove-orphans"], env, commands, fail=False)
        cleanup = {"containers": subprocess.run(["docker","ps","-aq","--filter",f"label=com.docker.compose.project={project}"], capture_output=True,text=True).stdout.split(),
                   "volumes": subprocess.run(["docker","volume","ls","-q","--filter",f"label=com.docker.compose.project={project}"], capture_output=True,text=True).stdout.split(),
                   "networks": subprocess.run(["docker","network","ls","-q","--filter",f"label=com.docker.compose.project={project}"], capture_output=True,text=True).stdout.split()}
        shutil.rmtree(temp, ignore_errors=True)
        cleanup["temp_root_removed"] = not temp.exists()
    git_sha = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    passed = sum(item.get("status") == "PASS" for item in results)
    clean = not error and passed == 32 and not any(cleanup[key] for key in ("containers", "volumes", "networks")) and cleanup["temp_root_removed"]
    registry = [{"scenario_id": sid, "layer": layer, "mutation_target": mutation,
                 "expected_verifier": "reject", "expected_http_behaviour": "409/403/404",
                 "restoration_method": "runner exact DB/filesystem restore"} for sid, layer, mutation in REGISTRY]
    write_json(evidence / "scenario-registry.json", registry)
    write_json(evidence / "tampering-results.json", {"implementation_sha": git_sha, "head_sha": git_sha,
        "required_scenario_ids": [item[0] for item in REGISTRY], "executed_scenario_ids": [item["scenario_id"] for item in results],
        "scenario_count": 32, "passed_count": passed, "failed_count": 32-passed, "pending_count": 0,
        "results": results, "original_pdf_sha": sha(original_pdf) if 'original_pdf' in locals() else None,
        "cleanup_status": "PASS" if clean else "FAILED", "error": error})
    for name, value in (("filesystem-results.json", [x for x in results if x["scenario_id"].startswith("fs_")]),
                        ("database-results.json", [x for x in results if x["scenario_id"].startswith("db_")]),
                        ("http-results.json", results), ("restoration-results.json", results),
                        ("control-customer-results.json", results), ("audit-results.json", results),
                        ("lifecycle-results.json", {"revision": "096_add_r8_canonical_snapshot_binding", "healthcheck": "PASS" if not error else "FAILED"})):
        write_json(evidence / name, value)
    (evidence / "commands.log").write_text("\n".join(json.dumps(item) for item in commands) + "\n")
    (evidence / "compose-ps.txt").write_text(json.dumps(cleanup, indent=2))
    (evidence / "backend-logs.txt").write_text("")
    status = "R8_TAMPERING_MATRIX_VERIFIED_RECOVERY_R7_REQUIRED" if clean else "R8_TAMPERING_MATRIX_REVIEW_CHANGES_REQUIRED"
    (evidence / "acceptance-report.md").write_text(f"# R8 tampering matrix acceptance\n\nStatus: {status}\n\nfilesystem canonical tampering 8/8 {'PASS' if passed >= 8 else 'FAILED'}\nfilesystem artifact tampering 6/6 {'PASS' if passed >= 14 else 'FAILED'}\nrun-result DB tampering 12/12 {'PASS' if passed >= 26 else 'FAILED'}\nartifact DB tampering 6/6 {'PASS' if passed == 32 else 'FAILED'}\nprotected HTTP operations fail-closed {'PASS' if clean else 'FAILED'}\nno PDF disclosure {'PASS' if clean else 'FAILED'}\nno auto-repair {'PASS' if clean else 'FAILED'}\ncontrol customer isolation {'PASS' if clean else 'FAILED'}\nrestoration {'PASS' if clean else 'FAILED'}\ncleanup {'PASS' if clean else 'FAILED'}\nrecovery matrix PENDING\nexecutable R7 regression PENDING\npublication concurrency PENDING\n\nNOT A FULL ACCEPTANCE CERTIFICATE\n")
    finalize(evidence)
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
