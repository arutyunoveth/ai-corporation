"""Fail-closed acceptance evidence for sequential final-PDF publication."""

# ruff: noqa: BLE001
from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import stat
import subprocess
import sys
import tempfile
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts" / "acceptance")]
from r8_acceptance.runtime import free_port, http
from run_r8_acceptance import _seed
from run_r9_application_restart import (
    COMPOSE,
    CUSTOMER,
    cleanup_runtime,
    run_command,
    run_hygiene_self_test,
    sanitize_text,
    sanitize_value,
    scan_hygiene,
    start_uvicorn,
    stop_uvicorn,
    utcnow,
    wait_for_health,
    write_json,
    write_sums,
)

SUCCESS = "R9_3_ARTIFACT_PUBLICATION_IDEMPOTENCY_PASS_LOCAL_FAIL_CLOSED_EVIDENCE_FINAL"
FILES = (
    "artifact-idempotency-result.json",
    "publication-attempts.json",
    "application-lifecycle.json",
    "database-snapshots.json",
    "audit-snapshots.json",
    "filesystem-snapshots.json",
    "verifier-results.json",
    "artifact-binding.json",
    "postgres-identity.json",
    "renderer-observation.json",
    "commands.log",
    "backend.log",
    "cleanup.json",
    "SHA256SUMS",
)
ARTIFACT_FIELDS = (
    "id",
    "customer_id",
    "project_id",
    "procurement_case_id",
    "run_id",
    "run_result_id",
    "artifact_type",
    "artifact_key",
    "report_model_hash",
    "source_graph_hash",
    "renderer_version",
    "manifest_relative_path",
    "manifest_file_sha256",
    "verification_policy_version",
    "pdf_relative_path",
    "pdf_sha256",
    "byte_size",
    "status",
    "created_at",
    "immutable_at",
)
RESULT_FIELDS = (
    "id",
    "customer_id",
    "project_id",
    "procurement_case_id",
    "run_id",
    "source_analysis_run_id",
    "canonical_report_storage_key",
    "canonical_report_hash",
    "source_graph_hash",
    "production_model_hash",
    "requirements_storage_key",
    "requirements_file_sha256",
    "canonical_report_file_sha256",
    "binding_manifest_storage_key",
    "binding_manifest_file_sha256",
    "source_graph_hash_algorithm",
    "report_model_hash",
    "verification_policy_version",
    "created_at",
    "completed_at",
)
TENDER_FIELDS = (
    "id",
    "registry_number",
    "status",
    "customer_id",
    "project_id",
    "procurement_case_id",
    "idempotency_key",
    "artifact_key",
    "source",
    "created_at",
    "updated_at",
)
CASE_FIELDS = (
    "id",
    "customer_id",
    "project_id",
    "procurement_number",
    "status",
    "artifact_key",
    "current_run_id",
    "error_message",
    "created_at",
    "updated_at",
)
AUDIT_FIELDS = (
    "id",
    "event_type",
    "customer_id",
    "project_id",
    "procurement_case_id",
    "run_id",
    "payload",
    "created_at",
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def value(obj: Any, fields: tuple[str, ...]) -> dict[str, Any]:
    return {field: getattr(obj, field, None) for field in fields}


def database_snapshot(dsn: str, state: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session

    from src.modules.customer_pilot.models import (
        PilotArtifact,
        PilotRunResult,
        ProcurementCase,
    )
    from src.tender_research.models import TenderAnalysisRun

    with Session(create_engine(dsn)) as session:
        artifact = session.get(PilotArtifact, state["artifact_id"])
        result = session.get(PilotRunResult, state["run_result_id"])
        run = session.get(TenderAnalysisRun, state["run_id"])
        case = session.get(ProcurementCase, state["case_id"])
        return {
            "scope": {
                key: state[key]
                for key in ("customer_id", "project_id", "case_id", "run_id")
            },
            "counts": {
                "PilotArtifact": session.scalar(
                    select(func.count())
                    .select_from(PilotArtifact)
                    .where(PilotArtifact.run_id == state["run_id"])
                ),
                "PilotRunResult": session.scalar(
                    select(func.count())
                    .select_from(PilotRunResult)
                    .where(PilotRunResult.run_id == state["run_id"])
                ),
                "TenderAnalysisRun": session.scalar(
                    select(func.count())
                    .select_from(TenderAnalysisRun)
                    .where(TenderAnalysisRun.id == state["run_id"])
                ),
                "ProcurementCase": session.scalar(
                    select(func.count())
                    .select_from(ProcurementCase)
                    .where(ProcurementCase.id == state["case_id"])
                ),
            },
            "PilotArtifact": value(artifact, ARTIFACT_FIELDS),
            "PilotRunResult": value(result, RESULT_FIELDS),
            "TenderAnalysisRun": value(run, TENDER_FIELDS),
            "ProcurementCase": value(case, CASE_FIELDS),
        }


def audit_snapshot(dsn: str, state: dict[str, Any]) -> dict[str, Any]:
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session

    from src.modules.customer_pilot.models import PilotAuditEvent

    with Session(create_engine(dsn)) as session:
        rows = session.scalars(
            select(PilotAuditEvent)
            .where(
                PilotAuditEvent.customer_id == state["customer_id"],
                PilotAuditEvent.project_id == state["project_id"],
                PilotAuditEvent.procurement_case_id == state["case_id"],
                PilotAuditEvent.run_id == state["run_id"],
            )
            .order_by(PilotAuditEvent.created_at, PilotAuditEvent.id)
        ).all()
    return {"count": len(rows), "rows": [value(row, AUDIT_FIELDS) for row in rows]}


def generation_snapshot(data_root: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    pdf_relative = Path(artifact["pdf_relative_path"])
    manifest_relative = Path(artifact["manifest_relative_path"])
    generation = data_root / pdf_relative.parent
    artifacts_root = generation.parent
    children = (
        sorted(path.name for path in artifacts_root.iterdir())
        if artifacts_root.is_dir()
        else []
    )
    dirs = (
        sorted(path.name for path in artifacts_root.iterdir() if path.is_dir())
        if artifacts_root.is_dir()
        else []
    )
    files: dict[str, Any] = {}
    for path in sorted(generation.iterdir()) if generation.is_dir() else []:
        info = path.lstat()
        files[path.name] = {
            "regular": stat.S_ISREG(info.st_mode),
            "mode": stat.S_IMODE(info.st_mode),
            "size": info.st_size,
            "sha256": digest(path) if stat.S_ISREG(info.st_mode) else None,
            "mtime_ns": info.st_mtime_ns,
        }
    manifest_path = data_root / manifest_relative
    pdf_path = data_root / pdf_relative
    manifest = (
        json.loads(manifest_path.read_text()) if manifest_path.is_file() else None
    )
    tree = sorted(
        str(path.relative_to(data_root))
        for path in data_root.rglob("*")
        if path.is_file()
    )
    return {
        "pdf_relative_path": str(pdf_relative),
        "manifest_relative_path": str(manifest_relative),
        "artifacts_root": str(artifacts_root.relative_to(data_root)),
        "generation": generation.name,
        "artifact_direct_children": children,
        "artifact_directories": dirs,
        "files": files,
        "pdf_sha256_actual": digest(pdf_path) if pdf_path.is_file() else None,
        "manifest_sha256_actual": digest(manifest_path)
        if manifest_path.is_file()
        else None,
        "manifest": manifest,
        "data_files": tree,
        "partial_or_temp_files": [
            p
            for p in tree
            if ".partial." in p or ".artifact." in p or ".r8-final-pdf" in p
        ],
    }


def verifier(env: dict[str, str], state: dict[str, Any]) -> dict[str, str]:
    code = """import json,os
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from src.modules.customer_pilot.models import PilotArtifact,PilotRunResult,ProcurementCase
from src.tender_research.models import TenderAnalysisRun
from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
from src.modules.customer_pilot.artifacts import verified_pilot_artifact
s=json.loads(os.environ['R9_STATE'])
with Session(create_engine(os.environ['AI_CORP_DATABASE_URL'])) as x:
 r=x.get(PilotRunResult,s['run_result_id']);a=x.get(PilotArtifact,s['artifact_id']);c=x.get(ProcurementCase,s['case_id']);run=x.get(TenderAnalysisRun,s['run_id']);verify_run_snapshot_binding(run=run,case=c,binding=r);verified_pilot_artifact(run,c,r,a);print(json.dumps({'canonical':'PASS','artifact':'PASS'}))"""
    run_env = env.copy()
    run_env["R9_STATE"] = json.dumps(state, default=str)
    completed = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        env=run_env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        raise RuntimeError(completed.stderr)
    return json.loads(completed.stdout)


def validate_manifest(snapshot: dict[str, Any], db: dict[str, Any]) -> bool:
    artifact, result, run, case = (
        db["PilotArtifact"],
        db["PilotRunResult"],
        db["TenderAnalysisRun"],
        db["ProcurementCase"],
    )
    manifest = snapshot.get("manifest")
    if not isinstance(manifest, dict):
        return False
    expected = {
        "customer_id": artifact["customer_id"],
        "project_id": artifact["project_id"],
        "procurement_case_id": artifact["procurement_case_id"],
        "run_id": artifact["run_id"],
        "run_result_id": artifact["run_result_id"],
        "artifact_key": artifact["artifact_key"],
        "artifact_type": artifact["artifact_type"],
        "renderer_version": artifact["renderer_version"],
        "report_model_hash": artifact["report_model_hash"],
        "source_graph_hash": artifact["source_graph_hash"],
        "pdf_relative_path": artifact["pdf_relative_path"],
        "pdf_sha256": artifact["pdf_sha256"],
        "byte_size": artifact["byte_size"],
        "registry_number": run.get("registry_number"),
        "source_analysis_run_id": result.get("source_analysis_run_id"),
        "requirements_storage_key": result.get("requirements_storage_key"),
        "requirements_file_sha256": result.get("requirements_file_sha256"),
        "canonical_report_storage_key": result.get("canonical_report_storage_key"),
        "canonical_report_file_sha256": result.get("canonical_report_file_sha256"),
        "binding_manifest_storage_key": result.get("binding_manifest_storage_key"),
        "binding_manifest_file_sha256": result.get("binding_manifest_file_sha256"),
        "source_graph_hash_algorithm": result.get("source_graph_hash_algorithm"),
        "production_model_hash": result.get("production_model_hash"),
    }
    return (
        all(manifest.get(key) == item for key, item in expected.items())
        and snapshot["pdf_sha256_actual"] == artifact["pdf_sha256"]
        and snapshot["files"].get("final.pdf", {}).get("size") == artifact["byte_size"]
        and snapshot["manifest_sha256_actual"] == artifact["manifest_file_sha256"]
        and snapshot["pdf_relative_path"] == artifact["pdf_relative_path"]
        and snapshot["manifest_relative_path"] == artifact["manifest_relative_path"]
        and case["current_run_id"] == artifact["run_id"]
    )


def validate_sha256sums(evidence: Path) -> dict[str, Any]:
    sums = evidence / "SHA256SUMS"
    expected = {name for name in FILES if name != "SHA256SUMS"}
    if not sums.is_file():
        return {"valid": False, "reason": "missing"}
    rows = [line.split("  ", 1) for line in sums.read_text().splitlines() if line]
    names = [row[1] for row in rows if len(row) == 2]
    parsed = {row[1]: row[0] for row in rows if len(row) == 2}
    valid = (
        len(rows) == len(expected)
        and len(names) == len(set(names))
        and set(names) == expected
        and all(
            "/" not in name
            and name != "SHA256SUMS"
            and (evidence / name).is_file()
            and digest(evidence / name) == parsed.get(name)
            for name in expected
        )
    )
    return {
        "valid": valid,
        "expected": sorted(expected),
        "listed": sorted(names),
        "duplicates": sorted({n for n in names if names.count(n) > 1}),
        "self_included": "SHA256SUMS" in names,
    }


def safe_write(
    path: Path,
    payload: Any,
    failures: list[dict[str, str]],
    secrets_map: dict[str, str],
    inject: str | None = None,
) -> None:
    try:
        if inject == path.name:
            raise OSError("injected optional evidence write failure")
        write_json(path, sanitize_value(payload, secrets_map))
    except Exception as exc:  # finalization must never mask the primary failure
        failures.append(
            {
                "file": path.name,
                "type": type(exc).__name__,
                "message": sanitize_text(exc, secrets_map),
            }
        )


def self_test_failure_finalization() -> bool:
    root = Path(tempfile.mkdtemp(prefix="r9-finalization-"))
    secrets_map = {
        "password": "self-test-password",
        "database_url": "postgresql://self-test",
        "temporary_root": str(root),
        "authorization": "Authorization: Basic Og==",
    }
    try:
        for injected in (None, "optional.json"):
            failures: list[dict[str, str]] = []
            primary = {
                "type": "RuntimeError",
                "message": "pre-start workflow error",
                "traceback": "sanitized",
                "stage": "pre-start",
                "operation": "self-test",
                "timestamp": utcnow(),
            }
            safe_write(
                root / "required.json",
                {"primary_failure": primary},
                failures,
                secrets_map,
            )
            safe_write(
                root / "optional.json", {"ok": True}, failures, secrets_map, injected
            )
            if not (root / "required.json").is_file() or (
                injected is not None and not failures
            ):
                return False
        return True
    finally:
        shutil.rmtree(root, ignore_errors=True)


def assertions(data: dict[str, Any]) -> dict[str, bool]:
    attempts, dbs, audits, fss, verifiers = (
        data["attempts"],
        data["database"],
        data["audit"],
        data["filesystem"],
        data["verifier"],
    )
    first_db, first_fs, first_audit = dbs[0], fss[0], audits[0]
    ids = [item.get("artifact_id") for item in attempts]
    return {
        "four_attempts_exact": len(attempts) == 4,
        "three_replays_exact": len(attempts[1:]) == 3,
        "all_http_201": len(attempts) == 4
        and all(item.get("http_status") == 201 for item in attempts),
        "same_response_identity": len(attempts) == 4
        and len(set(ids)) == 1
        and len({item.get("artifact_key") for item in attempts}) == 1,
        "snapshot_completeness": all(
            len(items) == 4 for items in (dbs, audits, fss, verifiers)
        ),
        "database_unchanged": len(dbs) == 4
        and all(item == first_db for item in dbs[1:]),
        "audit_unchanged": len(audits) == 4
        and all(item == first_audit for item in audits[1:]),
        "filesystem_unchanged": len(fss) == 4
        and all(item == first_fs for item in fss[1:]),
        "one_each_db_row": first_db["counts"]
        == {
            "PilotArtifact": 1,
            "PilotRunResult": 1,
            "TenderAnalysisRun": 1,
            "ProcurementCase": 1,
        },
        "one_export_audit": sum(
            row["event_type"] == "artifact_exported" for row in first_audit["rows"]
        )
        == 1,
        "no_extra_publication_events": sum(
            "artifact" in row["event_type"] for row in first_audit["rows"]
        )
        == 1,
        "one_strict_generation": first_fs["artifact_directories"]
        == [first_db["PilotArtifact"]["artifact_key"]]
        and first_fs["artifact_direct_children"]
        == [first_db["PilotArtifact"]["artifact_key"]],
        "strict_file_set": set(first_fs["files"])
        == {"final.pdf", "artifact.manifest.json"}
        and all(item["regular"] for item in first_fs["files"].values()),
        "no_partial_or_temp": first_fs["partial_or_temp_files"] == [],
        "manifest_matches_real_files_and_db": validate_manifest(first_fs, first_db),
        "verifiers_pass": len(verifiers) == 4
        and all(
            item == {"canonical": "PASS", "artifact": "PASS"} for item in verifiers
        ),
        "primary_failure_absent": data.get("primary_failure") is None,
        "finalization_failures_empty": data["finalization_failures"] == [],
        "cleanup_errors_empty": data["cleanup_errors"] == [],
        "cleanup_complete": data.get("cleanup", {}).get("compose_down_exit_code") == 0
        and data.get("cleanup", {}).get("temporary_directory_removed") is True,
    }


def main() -> int:
    evidence = (
        ROOT
        / "output"
        / f"r9-artifact-idempotency-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}"
    )
    evidence.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="r9-idempotency-", dir=ROOT / "output"))
    data_root = temp / "data"
    data_root.mkdir()
    postgres_port, app_port = free_port(), free_port()
    password = "r9-" + secrets.token_urlsafe(20)
    project = "r9idem" + secrets.token_hex(5)
    dsn = f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{postgres_port}/r8_acceptance"
    secrets_map = {
        "password": password,
        "database_url": dsn,
        "temporary_root": str(temp),
        "authorization": "Authorization: Basic Og==",
    }
    env = os.environ.copy()
    env.update(
        {
            "R8_POSTGRES_PASSWORD": password,
            "R8_POSTGRES_PORT": str(postgres_port),
            "AI_CORP_DATABASE_URL": dsn,
            "AI_CORP_ARVECTUM_DATA_DIR": str(data_root),
            "AI_CORP_PILOT_AUTH_ENABLED": "false",
            "AI_CORP_TENDER_PILOT_BASIC_AUTH_ENABLED": "false",
        }
    )
    data: dict[str, Any] = {
        "attempts": [],
        "database": [],
        "audit": [],
        "filesystem": [],
        "verifier": [],
        "lifecycle": {},
        "cleanup_errors": [],
        "finalization_failures": [],
        "primary_failure": None,
    }
    commands: list[dict[str, Any]] = []
    process = None
    try:
        compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
        run_command(compose + ["up", "-d", "--wait"], env, commands, secrets_map)
        run_command(
            [
                sys.executable,
                "-m",
                "alembic",
                "upgrade",
                "096_add_r8_canonical_snapshot_binding",
            ],
            env,
            commands,
            secrets_map,
        )
        _seed(env)
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from src.modules.customer_registry.models import CustomerProfile

        with Session(create_engine(dsn)) as session:
            session.add(
                CustomerProfile(
                    customer_id=CUSTOMER,
                    legal_name="R9 synthetic customer",
                    customer_status="prospect",
                )
            )
            session.commit()
        process = start_uvicorn(
            env, app_port, evidence / "backend.log", data["lifecycle"]
        )
        if wait_for_health(process, app_port, data["lifecycle"]) != 200:
            raise RuntimeError("health did not become 200")
        base = f"http://127.0.0.1:{app_port}/api/operator/pilot/customers/{CUSTOMER}"

        def post(path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
            status, raw, _ = http(
                "POST",
                base + path,
                username="",
                password="",
                body=body,
                headers={"Idempotency-Key": "r9-idempotency"}
                if path.endswith("/runs")
                else None,
            )
            if status not in {200, 201}:
                raise RuntimeError(f"{path}: {status} {raw}")
            return json.loads(raw)

        project_row = post("/projects", {"name": "R9 idempotency"})
        case_row = post(
            f"/projects/{project_row['id']}/cases",
            {"procurement_number": "0379100000726000101"},
        )
        run_row = post(f"/cases/{case_row['id']}/runs", {})
        completed = post(f"/cases/{case_row['id']}/runs/{run_row['id']}/complete", {})
        state = {
            "customer_id": CUSTOMER,
            "project_id": project_row["id"],
            "case_id": case_row["id"],
            "run_id": run_row["id"],
            "run_result_id": completed["run_result_id"],
        }
        endpoint = f"{base}/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf"
        for attempt in range(1, 5):
            started = utcnow()
            status, raw, _ = http("POST", endpoint, username="", password="")
            response = json.loads(raw)
            if status != 201:
                raise RuntimeError(f"publication {attempt}: {status} {raw}")
            state["artifact_id"] = response["id"]
            db = database_snapshot(dsn, state)
            fs = generation_snapshot(data_root, db["PilotArtifact"])
            data["attempts"].append(
                {
                    "attempt": attempt,
                    "requested_at": started,
                    "completed_at": utcnow(),
                    "http_status": status,
                    "response": response,
                    "artifact_id": response["id"],
                    "artifact_key": response["artifact_key"],
                }
            )
            data["database"].append(db)
            data["audit"].append(audit_snapshot(dsn, state))
            data["filesystem"].append(fs)
            data["verifier"].append(verifier(env, state))
        data["binding"] = data["database"][0]["PilotArtifact"]
    except Exception as exc:
        data["primary_failure"] = {
            "type": type(exc).__name__,
            "message": sanitize_text(exc, secrets_map),
            "traceback": sanitize_text(traceback.format_exc(), secrets_map),
            "stage": "workflow",
            "operation": "r9-artifact-idempotency",
            "timestamp": utcnow(),
        }
    finally:
        try:
            stop_uvicorn(process, data["lifecycle"])
        except Exception as exc:
            data["cleanup_errors"].append(sanitize_text(exc, secrets_map))
        try:
            data["cleanup"] = cleanup_runtime(
                project, temp, evidence, env, commands, secrets_map
            )
        except Exception as exc:
            data["cleanup_errors"].append(sanitize_text(exc, secrets_map))
            data["cleanup"] = {}
        payloads = {
            "publication-attempts.json": data["attempts"],
            "application-lifecycle.json": data["lifecycle"],
            "database-snapshots.json": data["database"],
            "audit-snapshots.json": data["audit"],
            "filesystem-snapshots.json": data["filesystem"],
            "verifier-results.json": data["verifier"],
            "artifact-binding.json": data.get("binding", {}),
            "postgres-identity.json": {},
            "renderer-observation.json": {
                "generation_created_once": len(data["filesystem"]) == 4,
                "regression_test": "test_sequential_final_pdf_replays_are_side_effect_free",
            },
            "commands.log": commands,
            "cleanup.json": data.get("cleanup", {}),
        }
        for name, payload in payloads.items():
            safe_write(
                evidence / name, payload, data["finalization_failures"], secrets_map
            )
        backend = evidence / "backend.log"
        try:
            backend.write_text(
                sanitize_text(
                    backend.read_text(errors="replace") if backend.exists() else "",
                    secrets_map,
                )
            )
        except Exception as exc:
            data["finalization_failures"].append(
                {
                    "file": "backend.log",
                    "type": type(exc).__name__,
                    "message": sanitize_text(exc, secrets_map),
                }
            )
        checks = (
            assertions(data)
            if len(data["database"]) == 4
            else {"workflow_complete": False}
        )
        first_hits = scan_hygiene(evidence, secrets_map)
        checks["evidence_hygiene_pass"] = first_hits == []
        result = {
            "status": "FAILED",
            "assertions": checks,
            "primary_failure": data["primary_failure"],
            "finalization_failures": data["finalization_failures"],
            "cleanup_errors": data["cleanup_errors"],
            "first_hygiene_hits": first_hits,
            "final_hygiene_hits": [],
        }
        safe_write(
            evidence / "artifact-idempotency-result.json",
            result,
            data["finalization_failures"],
            secrets_map,
        )
        try:
            write_sums(evidence)
        except Exception as exc:
            data["finalization_failures"].append(
                {
                    "file": "SHA256SUMS",
                    "type": type(exc).__name__,
                    "message": sanitize_text(exc, secrets_map),
                }
            )
        sums = validate_sha256sums(evidence)
        checks["sha256sums_complete_and_valid"] = sums["valid"]
        checks["evidence_pack_complete"] = all(
            (evidence / name).exists() for name in FILES
        )
        result["final_hygiene_hits"] = scan_hygiene(evidence, secrets_map)
        checks["evidence_hygiene_pass"] = result["final_hygiene_hits"] == []
        result["finalization_failures"] = data["finalization_failures"]
        result["status"] = (
            SUCCESS
            if data["primary_failure"] is None
            and not data["finalization_failures"]
            and not data["cleanup_errors"]
            and all(checks.values())
            else "FAILED"
        )
        safe_write(
            evidence / "artifact-idempotency-result.json",
            result,
            data["finalization_failures"],
            secrets_map,
        )
        write_sums(evidence)
    print(evidence)
    return 0 if result["status"] == SUCCESS else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test-hygiene", action="store_true")
    parser.add_argument("--self-test-failure-finalization", action="store_true")
    args = parser.parse_args()
    if args.self_test_hygiene:
        raise SystemExit(0 if run_hygiene_self_test() else 1)
    if args.self_test_failure_finalization:
        raise SystemExit(0 if self_test_failure_finalization() else 1)
    raise SystemExit(main())
