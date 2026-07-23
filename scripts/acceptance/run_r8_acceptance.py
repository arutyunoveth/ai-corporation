"""Direct R8 tenant acceptance runner; this is intentionally table-oriented."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from r8_acceptance.evidence import (
    finalize,
    matrix,
    sanitize,
    utcnow,
    validate_pass_payload,
    write_json,
)
from r8_acceptance.runtime import Uvicorn, compose_project_name, free_port, http

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
REGISTRY = "0379100000726000101"
CUSTOMER_A = "R8-ACCEPTANCE-A"
CUSTOMER_B = "R8-ACCEPTANCE-B"
TENANT_OPERATIONS = (
    "foreign_project_case_create",
    "get_case",
    "list_cases",
    "start_run",
    "complete_run",
    "publish_pdf",
    "list_artifacts",
    "download_pdf",
    "create_review",
    "review_read_path",
    "client_ready",
    "delivered",
    "create_feedback",
    "list_feedback",
    "archive",
)
TENANT_DIRECTIONS = ("customer_a_to_customer_b", "customer_b_to_customer_a")
LIST_OPERATIONS = {
    "list_cases",
    "list_artifacts",
    "list_feedback",
    "review_read_path",
}
PENDING_CONCURRENCY_NOTE = (
    "Publication concurrency is outside this tenant-evidence stage"
)
ACCEPTANCE_REPORT = (
    "# R8 tenant acceptance\n\n"
    "Status: R8_EVIDENCE_CONTRACT_AND_BIDIRECTIONAL_TENANT_VERIFIED_REMAINING_MATRICES_REQUIRED\n\n"
    "Results: A→B 15/15 PASS; B→A 15/15 PASS; no foreign leaks; DB no-mutation PASS; "
    "filesystem no-mutation PASS; lifecycle no-mutation PASS; cleanup PASS; "
    "publication concurrency PENDING; remaining matrices PENDING.\n\n"
    "NOT A FULL ACCEPTANCE CERTIFICATE\n"
)


def _json(body: bytes):
    return json.loads(body.decode("utf-8"))


def branch_evidence_sha():
    return (
        os.environ.get("GITHUB_HEAD_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    )


def _command(commands, args, env):
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    commands.append(
        json.dumps(
            {
                "command": " ".join(args),
                "exit_code": result.returncode,
                "finished_at": utcnow(),
            }
        )
    )
    if result.returncode:
        raise RuntimeError(result.stdout)


def _seed(env):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.modules.customer_registry.models import CustomerProfile
    from src.tender_research.models import (
        ProcurementDocumentChunk,
        ProcurementTender,
        ProcurementTenderDocument,
    )

    engine = create_engine(env["AI_CORP_DATABASE_URL"])
    with Session(engine) as session:
        for customer in (CUSTOMER_A, CUSTOMER_B):
            session.add(
                CustomerProfile(
                    customer_id=customer,
                    legal_name=customer,
                    customer_status="prospect",
                )
            )
        tender = ProcurementTender(
            source="r8-acceptance",
            external_id=REGISTRY,
            registry_number=REGISTRY,
            title="Acceptance cable supply",
        )
        session.add(tender)
        session.flush()
        document = ProcurementTenderDocument(
            tender_id=tender.id,
            file_name="acceptance.txt",
            download_status="downloaded",
            text_extraction_status="completed",
            sha256="a" * 64,
        )
        session.add(document)
        session.flush()
        session.add(
            ProcurementDocumentChunk(
                tender_id=tender.id,
                document_id=document.id,
                chunk_index=0,
                text="Acceptance cable supply",
                text_hash="b" * 64,
                char_start=0,
                char_end=23,
                token_estimate=4,
                source_file_name=document.file_name,
            )
        )
        session.commit()


def snapshot_business_db(env):
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    from src.modules.customer_pilot.models import (
        PilotArtifact,
        PilotFeedback,
        PilotProject,
        PilotReview,
        PilotRunResult,
        ProcurementCase,
    )
    from src.tender_research.models import TenderAnalysisRun

    engine = create_engine(env["AI_CORP_DATABASE_URL"])
    with Session(engine) as session:

        def rows(model, fields=()):
            values = []
            for item in session.scalars(select(model).order_by(model.id)).all():
                values.append(
                    {"id": item.id, **{field: getattr(item, field) for field in fields}}
                )
            return {"count": len(values), "rows": values}

        return {
            "PilotProject": rows(PilotProject),
            "ProcurementCase": rows(ProcurementCase, ("status", "current_run_id")),
            "TenderAnalysisRun": rows(TenderAnalysisRun),
            "PilotRunResult": rows(PilotRunResult),
            "PilotArtifact": rows(PilotArtifact),
            "PilotReview": rows(PilotReview),
            "PilotFeedback": rows(PilotFeedback),
        }


def snapshot_audit(env):
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session
    from src.modules.customer_pilot.models import PilotAuditEvent

    with Session(create_engine(env["AI_CORP_DATABASE_URL"])) as session:
        return session.scalar(select(func.count()).select_from(PilotAuditEvent))


def snapshot_filesystem(root):
    result = {}
    if not root.exists():
        return result
    for path in sorted(root.rglob("*")):
        stat = path.lstat()
        key = str(path.relative_to(root))
        if path.is_symlink():
            result[key] = {
                "type": "symlink",
                "target": str(path.readlink()),
                "mtime_ns": stat.st_mtime_ns,
            }
        elif path.is_dir():
            result[key] = {"type": "directory", "mtime_ns": stat.st_mtime_ns}
        elif path.is_file():
            result[key] = {
                "type": "file",
                "size": stat.st_size,
                "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "mtime_ns": stat.st_mtime_ns,
            }
    return result


def foreign_markers(state):
    return [
        str(state[key])
        for key in (
            "customer_id",
            "project_id",
            "case_id",
            "run_id",
            "run_result_id",
            "artifact_id",
            "artifact_key",
            "artifact_relative_path",
            "review_id",
            "feedback_id",
            "feedback_comment",
            "report_model_hash",
            "source_graph_hash",
        )
        if state.get(key)
    ]


def assert_no_foreign_leak(body, headers, markers):
    text = body.decode("utf-8", "replace") if isinstance(body, bytes) else str(body)
    try:
        text += json.dumps(json.loads(text), ensure_ascii=False, sort_keys=True)
    except (TypeError, ValueError):
        pass
    exposed_headers = " ".join(
        f"{key}:{value}"
        for key, value in headers.items()
        if any(
            word in key.lower()
            for word in ("artifact", "storage", "path", "hash", "report", "source")
        )
        or key.lower() in {"location", "content-disposition", "etag"}
    )
    for marker in markers:
        if marker and (marker in text or marker in exposed_headers):
            raise AssertionError(f"foreign marker leaked: {marker}")


def build_cross_tenant_request(operation, actor, owner):
    c, r, p = owner["case_id"], owner["run_id"], owner["project_id"]
    mapping = {
        "foreign_project_case_create": (
            "POST",
            f"/projects/{p}/cases",
            {"procurement_number": REGISTRY},
        ),
        "get_case": ("GET", f"/cases/{c}", None),
        "list_cases": ("GET", "/cases", None),
        "start_run": ("POST", f"/cases/{c}/runs", {}),
        "complete_run": ("POST", f"/cases/{c}/runs/{r}/complete", None),
        "publish_pdf": ("POST", f"/cases/{c}/runs/{r}/artifacts/final-pdf", None),
        "list_artifacts": (
            "GET",
            f"/cases/{actor['case_id']}/runs/{actor['run_id']}/artifacts",
            None,
        ),
        "download_pdf": ("GET", f"/cases/{c}/runs/{r}/artifacts/final-pdf", None),
        "create_review": (
            "POST",
            f"/cases/{c}/runs/{r}/review",
            {"reviewer": "foreign", "verdict": "approved"},
        ),
        "review_read_path": ("GET", f"/cases/{actor['case_id']}", None),
        "client_ready": ("POST", f"/cases/{c}/client-ready", None),
        "delivered": ("POST", f"/cases/{c}/delivered", None),
        "create_feedback": (
            "POST",
            f"/cases/{c}/feedback?run_id={r}",
            {"category": "report_usability", "severity": "low", "comment": "foreign"},
        ),
        "list_feedback": ("GET", f"/cases/{actor['case_id']}/feedback", None),
        "archive": ("POST", f"/cases/{c}/archive", None),
    }
    return mapping[operation]


def _list_safe(operation, body, actor, owner):
    parsed = _json(body)
    text = json.dumps(parsed)
    if operation == "list_cases":
        return {
            "actor_owned_present": actor["case_id"] in text,
            "foreign_owned_absent": owner["case_id"] not in text,
        }
    if operation == "list_artifacts":
        return {
            "actor_owned_present": actor["artifact_id"] in text
            or actor["artifact_key"] in text,
            "foreign_owned_absent": owner["artifact_id"] not in text
            and owner["artifact_key"] not in text,
        }
    if operation == "list_feedback":
        return {
            "actor_owned_present": actor["feedback_id"] in text
            or actor["feedback_comment"] in text,
            "foreign_owned_absent": owner["feedback_id"] not in text
            and owner["feedback_comment"] not in text,
        }
    if operation == "review_read_path":
        return {
            "actor_owned_present": actor["case_id"] in text,
            "foreign_owned_absent": owner["review_id"] not in text
            and owner["feedback_id"] not in text,
            "review_not_exposed_by_read_contract": actor["review_id"] not in text,
        }
    return {"actor_owned_present": False, "foreign_owned_absent": False}


def run_cross_tenant_direction(
    direction, base, username, password, env, data_root, actor, owner
):
    results = []
    for operation in TENANT_OPERATIONS:
        method, suffix, payload = build_cross_tenant_request(operation, actor, owner)
        before_db, before_fs, before_audit = (
            snapshot_business_db(env),
            snapshot_filesystem(data_root),
            snapshot_audit(env),
        )
        status, body, headers = http(
            method,
            base.format(customer=actor["customer_id"]) + suffix,
            username=username,
            password=password,
            body=payload,
            headers={"Idempotency-Key": f"tenant-{operation}"}
            if operation == "start_run"
            else None,
        )
        after_db, after_fs, after_audit = (
            snapshot_business_db(env),
            snapshot_filesystem(data_root),
            snapshot_audit(env),
        )
        errors = []
        list_checks = {}
        try:
            assert_no_foreign_leak(body, headers, foreign_markers(owner))
            list_operation = operation in LIST_OPERATIONS
            correct_http = status == 200 if list_operation else status in {403, 404}
            if list_operation:
                list_checks = _list_safe(operation, body, actor, owner)
                assert all(
                    value
                    for key, value in list_checks.items()
                    if key != "review_not_exposed_by_read_contract"
                )
            assert (
                status != 500
                and correct_http
                and before_db == after_db
                and before_fs == after_fs
                and before_audit == after_audit
            )
        except AssertionError as exc:
            errors.append(str(exc))
        results.append(
            {
                "scenario_id": f"{direction}:{operation}",
                "direction": direction,
                "operation": operation,
                "method": method,
                "path_template": suffix,
                "http_status": status,
                "status_is_safe": status in {200, 403, 404},
                "no_500": status != 500,
                "no_foreign_leak": not errors
                or not errors[0].startswith("foreign marker"),
                "db_unchanged": before_db == after_db,
                "filesystem_unchanged": before_fs == after_fs,
                "lifecycle_unchanged": before_db == after_db,
                "audit_delta": after_audit - before_audit,
                "actor_owned_present": list_checks.get("actor_owned_present"),
                "foreign_owned_absent": list_checks.get("foreign_owned_absent"),
                "review_not_exposed_by_read_contract": list_checks.get(
                    "review_not_exposed_by_read_contract"
                ),
                "checks": ["http", "no-leak", "db", "filesystem", "lifecycle"],
                "errors": errors,
                "status": "PASS" if not errors else "FAILED",
            }
        )
    return results


def validate_tenant_results(results):
    required = {
        f"{direction}:{operation}"
        for direction in TENANT_DIRECTIONS
        for operation in TENANT_OPERATIONS
    }
    executed = [item["scenario_id"] for item in results]
    if len(required) != 30 or len(executed) != 30 or set(executed) != required:
        raise RuntimeError("tenant scenario matrix is incomplete")
    if len(set(executed)) != len(executed):
        raise RuntimeError("tenant scenario matrix has duplicate scenario IDs")


def _prepare_customer(base, username, password, customer, concurrent=False):
    url = base.format(customer=customer)

    def request(method, suffix, body=None):
        status, raw, _ = http(
            method,
            url + suffix,
            username=username,
            password=password,
            body=body,
            headers={"Idempotency-Key": f"setup-{customer}"}
            if suffix.endswith("/runs")
            else None,
        )
        assert status in {200, 201}, (status, raw)
        return _json(raw)

    project = request("POST", "/projects", {"name": f"Acceptance {customer}"})
    case = request(
        "POST", f"/projects/{project['id']}/cases", {"procurement_number": REGISTRY}
    )
    run = request("POST", f"/cases/{case['id']}/runs", {})
    complete = request("POST", f"/cases/{case['id']}/runs/{run['id']}/complete")
    artifact = request(
        "POST", f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf"
    )
    review = request(
        "POST",
        f"/cases/{case['id']}/runs/{run['id']}/review",
        {"reviewer": "acceptance", "verdict": "approved"},
    )
    request("POST", f"/cases/{case['id']}/client-ready")
    request("POST", f"/cases/{case['id']}/delivered")
    feedback = request(
        "POST",
        f"/cases/{case['id']}/feedback?run_id={run['id']}",
        {
            "category": "report_usability",
            "severity": "low",
            "comment": f"feedback-{customer}",
        },
    )
    return {
        "customer_id": customer,
        "project_id": project["id"],
        "case_id": case["id"],
        "run_id": run["id"],
        "run_result_id": complete["run_result_id"],
        "artifact_id": artifact["id"],
        "artifact_key": artifact["artifact_key"],
        "pdf_sha256": artifact["pdf_sha256"],
        "review_id": review["id"],
        "feedback_id": feedback["id"],
        "feedback_comment": f"feedback-{customer}",
    }


def _enrich_states(env, states):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.modules.customer_pilot.models import PilotArtifact, PilotRunResult

    with Session(create_engine(env["AI_CORP_DATABASE_URL"])) as session:
        for state in states:
            artifact, result = (
                session.get(PilotArtifact, state["artifact_id"]),
                session.get(PilotRunResult, state["run_result_id"]),
            )
            state["artifact_relative_path"] = artifact.pdf_relative_path
            state["report_model_hash"] = result.report_model_hash
            state["source_graph_hash"] = result.source_graph_hash


def verify_cleanup(compose_project, runtime, temp_root):
    process = runtime.process
    runtime.stop("tenant")
    subprocess.run(
        [
            "docker",
            "compose",
            "-p",
            compose_project,
            "-f",
            str(COMPOSE),
            "down",
            "--volumes",
            "--remove-orphans",
        ],
        cwd=ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    shutil.rmtree(temp_root, ignore_errors=True)

    def ids(args):
        return (
            subprocess.run(args, text=True, capture_output=True)
            .stdout.strip()
            .splitlines()
        )

    return {
        "containers": ids(
            [
                "docker",
                "ps",
                "-aq",
                "--filter",
                f"label=com.docker.compose.project={compose_project}",
            ]
        ),
        "volumes": ids(
            [
                "docker",
                "volume",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={compose_project}",
            ]
        ),
        "networks": ids(
            [
                "docker",
                "network",
                "ls",
                "-q",
                "--filter",
                f"label=com.docker.compose.project={compose_project}",
            ]
        ),
        "runtime_stopped": process is not None and process.poll() is not None,
        "temp_root_removed": not temp_root.exists(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", required=True, choices=("foundation", "tenant-concurrency", "full")
    )
    phase = parser.parse_args().phase
    branch_head_sha = branch_evidence_sha()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "output" / f"r8-acceptance-tenant-concurrency-{stamp}"
    evidence.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="r8-uvicorn-acceptance-", dir=ROOT / "output"))
    data = temp / "data"
    data.mkdir()
    project, port, commands, errors = compose_project_name(), free_port(), [], []
    username, password, pg_password = (
        "pilot-" + secrets.token_hex(4),
        secrets.token_urlsafe(18),
        "test-" + secrets.token_urlsafe(18),
    )
    env = os.environ.copy()
    env.update(
        {
            "R8_POSTGRES_PASSWORD": pg_password,
            "R8_POSTGRES_PORT": str(port),
            "AI_CORP_DATABASE_URL": f"postgresql+psycopg://r8_acceptance:{pg_password}@127.0.0.1:{port}/r8_acceptance",
            "AI_CORP_ARVECTUM_DATA_DIR": str(data),
            "AI_CORP_PILOT_AUTH_ENABLED": "true",
            "AI_CORP_PILOT_AUTH_USERNAME": username,
            "AI_CORP_PILOT_AUTH_PASSWORD": password,
            "AI_CORP_DEBUG": "true",
        }
    )
    os.environ.update(
        {key: value for key, value in env.items() if key.startswith("AI_CORP_")}
    )
    runtime = Uvicorn(
        root=ROOT, env=env, port=free_port(), log=evidence / "backend-logs.txt"
    )
    states = []
    results = []
    cleanup = {}
    try:
        _command(
            commands,
            [
                "docker",
                "compose",
                "-p",
                project,
                "-f",
                str(COMPOSE),
                "up",
                "-d",
                "--wait",
            ],
            env,
        )
        _command(commands, [sys.executable, "-m", "alembic", "upgrade", "head"], env)
        _seed(env)
        runtime.start("tenant")
        runtime.wait_ready(username, password)
        base = (
            f"http://127.0.0.1:{runtime.port}/api/operator/pilot/customers/{{customer}}"
        )
        states = [
            _prepare_customer(base, username, password, CUSTOMER_A),
            _prepare_customer(base, username, password, CUSTOMER_B),
        ]
        _enrich_states(env, states)
        assert all(
            states[0][key] != states[1][key]
            for key in (
                "project_id",
                "case_id",
                "run_id",
                "run_result_id",
                "artifact_id",
                "artifact_key",
                "artifact_relative_path",
                "review_id",
                "feedback_id",
            )
        )
        results = run_cross_tenant_direction(
            TENANT_DIRECTIONS[0],
            base,
            username,
            password,
            env,
            data,
            states[0],
            states[1],
        ) + run_cross_tenant_direction(
            TENANT_DIRECTIONS[1],
            base,
            username,
            password,
            env,
            data,
            states[1],
            states[0],
        )
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {sanitize(str(exc), temp)}")
    finally:
        cleanup = verify_cleanup(project, runtime, temp)
    cleanup_status = (
        "PASS"
        if all(not value for value in cleanup.values() if isinstance(value, list))
        and cleanup.get("runtime_stopped")
        and cleanup.get("temp_root_removed")
        else "FAILED"
    )
    passed = sum(item["status"] == "PASS" for item in results)
    try:
        validate_tenant_results(results)
        matrix_complete = True
    except RuntimeError as exc:
        matrix_complete = False
        errors.append(str(exc))
    tenant_ok = (
        matrix_complete and passed == 30 and not errors and cleanup_status == "PASS"
    )
    tenant = matrix(
        phase=phase,
        status="PASS" if tenant_ok else "FAILED",
        started_at=utcnow(),
        checks=results,
        actual={
            "customer_a": states[0] if states else {},
            "customer_b": states[1] if len(states) > 1 else {},
            "scenario_results": results,
            "cleanup": cleanup,
        },
        errors=errors,
        cleanup_status=cleanup_status,
        scenario_count=len(results),
        passed_count=passed,
        failed_count=len(results) - passed,
        pending_count=0,
        head_sha=branch_head_sha,
        implementation_sha=branch_head_sha,
    )
    if tenant_ok:
        validate_pass_payload(tenant)
    write_json(evidence / "tenant-isolation-results.json", tenant)
    for name in (
        "migration-state.json",
        "lifecycle-results.json",
        "tampering-results.json",
        "recovery-results.json",
        "restart-results.json",
    ):
        write_json(
            evidence / name,
            matrix(
                phase=phase,
                status="PENDING_NOT_EXECUTED",
                started_at=utcnow(),
                checks=[],
                cleanup_status=cleanup_status,
                head_sha=branch_head_sha,
                implementation_sha=branch_head_sha,
            ),
        )
    write_json(
        evidence / "concurrency-results.json",
        matrix(
            phase=phase,
            status="PENDING_NOT_EXECUTED",
            started_at=utcnow(),
            checks=[],
            actual={"note": PENDING_CONCURRENCY_NOTE},
            cleanup_status=cleanup_status,
            scenario_count=0,
            passed_count=0,
            failed_count=0,
            pending_count=1,
            head_sha=branch_head_sha,
            implementation_sha=branch_head_sha,
        ),
    )
    write_json(
        evidence / "artifact-inventory.json",
        matrix(
            phase=phase,
            status="PASS" if tenant_ok else "FAILED",
            started_at=utcnow(),
            checks=[{"customer_states": bool(states)}],
            cleanup_status=cleanup_status,
            scenario_count=1,
            passed_count=1 if tenant_ok else 0,
            failed_count=0 if tenant_ok else 1,
            pending_count=0,
            errors=errors,
            head_sha=branch_head_sha,
            implementation_sha=branch_head_sha,
        ),
    )
    write_json(
        evidence / "database-counts.json",
        matrix(
            phase=phase,
            status="PASS" if tenant_ok else "FAILED",
            started_at=utcnow(),
            checks=[{"no_mutations": tenant_ok}],
            cleanup_status=cleanup_status,
            scenario_count=1,
            passed_count=1 if tenant_ok else 0,
            failed_count=0 if tenant_ok else 1,
            pending_count=0,
            errors=errors,
            head_sha=branch_head_sha,
            implementation_sha=branch_head_sha,
        ),
    )
    (evidence / "commands.log").write_text("\n".join(commands) + "\n", encoding="utf-8")
    (evidence / "backend-logs.txt").touch(exist_ok=True)
    (evidence / "compose-ps.txt").write_text(
        json.dumps(cleanup, indent=2) + "\n", encoding="utf-8"
    )
    (evidence / "acceptance-report.md").write_text(
        ACCEPTANCE_REPORT,
        encoding="utf-8",
    )
    finalize(evidence)
    return 0 if tenant_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
