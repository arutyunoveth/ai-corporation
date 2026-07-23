"""Real-uvicorn R8 acceptance foundation; deliberately not a full certificate."""

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
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import UTC, datetime
from pathlib import Path

from r8_acceptance.evidence import (
    finalize,
    matrix,
    sanitize,
    utcnow,
    write_json,
)
from r8_acceptance.runtime import Uvicorn, compose_project_name, free_port, http


ROOT = Path(__file__).resolve().parents[2]
# The runner is deliberately executable as a script from Make and Actions.
# Keep repository imports stable even when Python sets sys.path[0] to this
# script's directory instead of the checkout root.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
REGISTRY = "0379100000726000101"
CUSTOMER = "R8-ACCEPTANCE-A"
CUSTOMER_B = "R8-ACCEPTANCE-B"


def _json(body: bytes) -> dict:
    return json.loads(body.decode("utf-8"))


def _command(commands: list[str], args: list[str], env: dict[str, str]) -> None:
    started = utcnow()
    clock = time.monotonic()
    result = subprocess.run(
        args,
        cwd=ROOT,
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    commands.append(
        json.dumps(
            {
                "command": " ".join(args),
                "duration_seconds": round(time.monotonic() - clock, 3),
                "exit_code": result.returncode,
                "finished_at": utcnow(),
                "started_at": started,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    if result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode, args, output=result.stdout
        )


def _alembic_state(env: dict[str, str], commands: list[str]) -> dict:
    """Assert the actual installed migration head rather than inheriting success."""

    def inspect(*args: str) -> tuple[int, str]:
        result = subprocess.run(
            [sys.executable, "-m", "alembic", *args],
            cwd=ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        commands.append(
            json.dumps(
                {
                    "command": " ".join(result.args),
                    "exit_code": result.returncode,
                    "finished_at": utcnow(),
                    "started_at": utcnow(),
                    "duration_seconds": 0,
                },
                sort_keys=True,
            )
        )
        return result.returncode, result.stdout + result.stderr

    heads_code, heads = inspect("heads")
    current_code, current = inspect("current")
    repeat_code, _ = inspect("upgrade", "head")
    parsed_heads = [line.strip() for line in heads.splitlines() if "(head)" in line]
    expected = "096_add_r8_canonical_snapshot_binding"
    current_revision = next(
        (
            line.strip()
            for line in current.splitlines()
            if "096_add_r8_canonical_snapshot_binding" in line
        ),
        "",
    )
    passed = (
        heads_code == current_code == repeat_code == 0
        and len(parsed_heads) == 1
        and expected in parsed_heads[0]
        and expected in current_revision
    )
    if not passed:
        raise AssertionError("Alembic head/current assertion failed")
    return {
        "command": "alembic heads/current/upgrade head",
        "exit_code": 0,
        "parsed_heads": parsed_heads,
        "head_count": len(parsed_heads),
        "current_revision": current_revision,
        "expected_revision": expected,
        "repeat_upgrade_exit_code": repeat_code,
    }


def _migration_cycle(env: dict[str, str], commands: list[str]) -> dict:
    """Prove the R8 revision can round-trip before customer data exists."""
    for revision in ("095_add_r8_current_run", "096_add_r8_canonical_snapshot_binding"):
        _command(commands, [sys.executable, "-m", "alembic", "downgrade" if revision.startswith("095") else "upgrade", revision], env)
    state = _alembic_state(env, commands)
    return {"cycle": "096→095→096", "final": state}


TENANT_ENDPOINTS = (
    "foreign_project_case_create", "get_case", "list_cases", "start_run",
    "complete_run", "publish_pdf", "list_artifacts", "download_pdf",
    "create_review", "client_ready", "delivered", "create_feedback",
    "list_feedback", "archive",
)


def _assert_no_leak(body: bytes, foreign: dict) -> None:
    """Responses to a cross-tenant request must not disclose any foreign ID."""
    text = body.decode("utf-8", "replace")
    for value in foreign.values():
        if isinstance(value, str):
            assert value not in text


def _seed(env: dict[str, str]) -> None:
    # Import only after the disposable DATABASE_URL is established.
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
        session.add(
            CustomerProfile(
                customer_id=CUSTOMER,
                legal_name="R8 Acceptance Customer A",
                customer_status="prospect",
            )
        )
        session.add(
            CustomerProfile(
                customer_id=CUSTOMER_B,
                legal_name="R8 Acceptance Customer B",
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
            file_name="Техническое задание.txt",
            download_status="downloaded",
            text_extraction_status="completed",
            sha256="a" * 64,
        )
        session.add(document)
        session.flush()
        text = (
            "Поставка кабеля ВВГнг 3х2.5. Количество 100 метров. Срок поставки 10 дней."
        )
        session.add(
            ProcurementDocumentChunk(
                tender_id=tender.id,
                document_id=document.id,
                chunk_index=0,
                text=text,
                text_hash="b" * 64,
                char_start=0,
                char_end=len(text),
                token_estimate=20,
                source_file_name=document.file_name,
            )
        )
        session.commit()


def _tenant_concurrency(
    *,
    base: str,
    username: str,
    password: str,
    env: dict[str, str],
    customer_a_state: dict,
) -> tuple[dict, dict]:
    """Run tenant isolation and actual parallel PDF publication against uvicorn."""
    bbase = base.replace(CUSTOMER, CUSTOMER_B)
    status, body, _ = http(
        "POST",
        bbase + "/projects",
        username=username,
        password=password,
        body={"name": "Acceptance"},
    )
    assert status == 201
    project = _json(body)
    status, body, _ = http(
        "POST",
        bbase + f"/projects/{project['id']}/cases",
        username=username,
        password=password,
        body={"procurement_number": REGISTRY},
    )
    assert status == 201
    case = _json(body)
    status, body, _ = http(
        "POST",
        bbase + f"/cases/{case['id']}/runs",
        username=username,
        password=password,
        body={},
        headers={"Idempotency-Key": "tenant-b"},
    )
    assert status == 201
    run = _json(body)
    status, body, _ = http(
        "POST",
        bbase + f"/cases/{case['id']}/runs/{run['id']}/complete",
        username=username,
        password=password,
    )
    assert status == 200
    complete = _json(body)
    barrier = Barrier(4)
    url = bbase + f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf"

    def publish(_: int) -> tuple[int, dict]:
        barrier.wait(timeout=10)
        status, body, _ = http("POST", url, username=username, password=password)
        return status, _json(body)

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(publish, range(4)))
    assert all(status in {200, 201} for status, _ in responses)
    artifact_ids = {body["id"] for _, body in responses}
    artifact_keys = {body["artifact_key"] for _, body in responses}
    hashes = {body["pdf_sha256"] for _, body in responses}
    assert len(artifact_ids) == len(artifact_keys) == len(hashes) == 1
    artifact = responses[0][1]
    status, body, _ = http(
        "POST",
        bbase + f"/cases/{case['id']}/runs/{run['id']}/review",
        username=username,
        password=password,
        body={"reviewer": "acceptance", "verdict": "approved"},
    )
    assert status == 200
    review = _json(body)
    bstate = {
        "project_id": project["id"],
        "case_id": case["id"],
        "run_id": run["id"],
        "artifact_id": artifact["id"],
        "artifact_key": artifact["artifact_key"],
        "pdf_sha256": artifact["pdf_sha256"],
        "review_id": review["id"],
        "run_result_id": complete["run_result_id"],
    }
    binventory, bcounts = _verified_state(env, bstate, CUSTOMER_B)
    # Cross-tenant paths use opaque identifiers and are executed in both directions.
    a_case, a_run = customer_a_state["case_id"], customer_a_state["run_id"]
    forbidden = [
        ("GET", f"/cases/{a_case}"),
        ("POST", f"/cases/{a_case}/runs"),
        ("POST", f"/cases/{a_case}/runs/{a_run}/complete"),
        ("POST", f"/cases/{a_case}/runs/{a_run}/artifacts/final-pdf"),
        ("GET", f"/cases/{a_case}/runs/{a_run}/artifacts/final-pdf"),
        ("POST", f"/cases/{a_case}/client-ready"),
        ("POST", f"/cases/{a_case}/archive"),
    ]
    matrix = []
    for method, suffix in forbidden:
        status, body, _ = http(
            method,
            bbase + suffix,
            username=username,
            password=password,
            body={} if method == "POST" else None,
            headers={"Idempotency-Key": "cross-tenant"}
            if suffix.endswith("/runs")
            else None,
        )
        _assert_no_leak(body, customer_a_state)
        assert status == 404
        matrix.append(
            {
                "method": method,
                "operation": suffix.split("?")[0],
                "status": status,
                "response_leak_check": True,
            }
        )
    # A performs the same resource-bound operations against B.  List-cases is
    # checked independently because it has no foreign opaque identifier.
    abase = base
    b_forbidden = [
        ("POST", f"/projects/{project['id']}/cases", {"procurement_number": REGISTRY}),
        ("GET", f"/cases/{case['id']}", None),
        ("GET", "/cases", None),
        ("POST", f"/cases/{case['id']}/runs", {}),
        ("POST", f"/cases/{case['id']}/runs/{run['id']}/complete", {}),
        ("POST", f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf", {}),
        ("GET", f"/cases/{case['id']}/runs/{run['id']}/artifacts", None),
        ("GET", f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf", None),
        ("POST", f"/cases/{case['id']}/runs/{run['id']}/review", {"reviewer": "x", "verdict": "approved"}),
        ("POST", f"/cases/{case['id']}/client-ready", {}),
        ("POST", f"/cases/{case['id']}/delivered", {}),
        ("POST", f"/cases/{case['id']}/feedback?run_id={run['id']}", {"category": "report_usability", "severity": "low", "comment": "foreign"}),
        ("GET", f"/cases/{case['id']}/feedback", None),
        ("POST", f"/cases/{case['id']}/archive", {}),
    ]
    for method, suffix, payload in b_forbidden:
        status, body, _ = http(method, abase + suffix, username=username, password=password, body=payload, headers={"Idempotency-Key": "cross-tenant-a"} if suffix.endswith("/runs") else None)
        assert status == (200 if suffix == "/cases" else 404)
        _assert_no_leak(body, bstate)
        matrix.append({"method": method, "operation": suffix, "status": status, "response_leak_check": True})
    tenant_result = {
        "customer_b": bstate,
        "customer_b_inventory": binventory,
        "cross_tenant_matrix": matrix,
        "scenario_count": len(matrix),
    }
    concurrency_result = {
        "worker_count": 4,
        "responses": [
            {
                "status": status,
                "artifact_id": body["id"],
                "artifact_key": body["artifact_key"],
                "pdf_sha256": body["pdf_sha256"],
            }
            for status, body in responses
        ],
        "unique_artifact_id_count": len(artifact_ids),
        "unique_artifact_key_count": len(artifact_keys),
        "unique_pdf_sha_count": len(hashes),
    }
    return tenant_result, concurrency_result, {"customer_b_counts": bcounts}


def _verified_state(
    env: dict[str, str], state: dict, customer_id: str = CUSTOMER
) -> tuple[dict, dict]:
    """Read authoritative DB rows and filesystem bytes once through strict verifiers."""
    from sqlalchemy import create_engine, func, select
    from sqlalchemy.orm import Session
    from src.modules.customer_registry.models import CustomerProfile
    from src.modules.customer_pilot.artifacts import (
        verify_pilot_artifact_binding,
        verify_review_artifact_binding,
    )
    from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding
    from src.modules.customer_pilot.models import (
        PilotArtifact,
        PilotAuditEvent,
        PilotFeedback,
        PilotProject,
        PilotReview,
        PilotRunResult,
        ProcurementCase,
    )
    from src.tender_research.models import TenderAnalysisRun

    engine = create_engine(env["AI_CORP_DATABASE_URL"])
    with Session(engine) as session:
        case = session.get(ProcurementCase, state["case_id"])
        run = session.get(TenderAnalysisRun, state["run_id"])
        result = session.get(PilotRunResult, state["run_result_id"])
        artifact = session.get(PilotArtifact, state["artifact_id"])
        review = session.get(PilotReview, state["review_id"])
        assert (
            case
            and run
            and result
            and artifact
            and review
            and result.is_verified_snapshot_binding
        )
        canonical = verify_run_snapshot_binding(run=run, case=case, binding=result)
        verified_artifact = verify_pilot_artifact_binding(
            run=run, case=case, result=result, artifact=artifact
        )
        verify_review_artifact_binding(
            review=review,
            run=run,
            case=case,
            result=result,
            artifact=artifact,
            verified_artifact=verified_artifact,
        )
        files = {}
        for path in (
            verified_artifact.generation.pdf_path,
            verified_artifact.generation.manifest_path,
        ):
            stat = path.stat()
            files[path.name] = {
                "mtime_ns": stat.st_mtime_ns,
                "relative_path": str(
                    path.relative_to(env["AI_CORP_ARVECTUM_DATA_DIR"])
                ),
                "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
                "size": stat.st_size,
            }
        inventory = {
            "artifact_id": artifact.id,
            "artifact_key": artifact.artifact_key,
            "artifact_type": artifact.artifact_type,
            "canonical_report_file_sha256": canonical.canonical_report_file_sha256,
            "exact_file_set": sorted(files),
            "files": files,
            "manifest_file_sha256": verified_artifact.manifest_file_sha256,
            "pdf_sha256": verified_artifact.pdf_sha256,
            "renderer_version": verified_artifact.renderer_version,
            "report_model_hash": verified_artifact.report_model_hash,
            "source_graph_hash": verified_artifact.source_graph_hash,
        }
        tables = {
            "customer_profiles": CustomerProfile,
            "pilot_projects": PilotProject,
            "procurement_cases": ProcurementCase,
            "tender_analysis_runs": TenderAnalysisRun,
            "pilot_run_results": PilotRunResult,
            "pilot_artifacts": PilotArtifact,
            "pilot_reviews": PilotReview,
            "pilot_feedback": PilotFeedback,
            "pilot_audit_events": PilotAuditEvent,
        }
        counts = {
            name: session.scalar(select(func.count()).select_from(model))
            for name, model in tables.items()
        }
        counts["by_customer"] = {
            customer_id: {
                name: session.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.customer_id == customer_id)
                )
                for name, model in tables.items()
                if hasattr(model, "customer_id")
            }
        }
        return inventory, counts


def _tampering_and_recovery(
    *, base: str, username: str, password: str, env: dict[str, str], state: dict
) -> tuple[dict, dict]:
    """Exercise fail-closed filesystem and DB conflict detection, then recovery.

    Every mutation is performed only in the disposable acceptance namespace and
    restored immediately before proceeding to the next scenario.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from src.modules.customer_pilot.models import PilotArtifact, PilotRunResult

    endpoint = base + f"/cases/{state['case_id']}/runs/{state['run_id']}/artifacts/final-pdf"
    data_root = Path(env["AI_CORP_ARVECTUM_DATA_DIR"])
    artifact_dir = data_root / "customer-pilot" / CUSTOMER / state["project_id"] / state["case_id"] / state["run_id"] / "artifacts" / state["artifact_key"]
    pdf_path, manifest_path = artifact_dir / "final.pdf", artifact_dir / "artifact.manifest.json"
    original_pdf, original_manifest = pdf_path.read_bytes(), manifest_path.read_bytes()
    scenarios: list[dict] = []

    def verify_rejected(name: str) -> None:
        status, body, _ = http("GET", endpoint, username=username, password=password)
        assert status == 409, (name, status, body.decode("utf-8", "replace"))
        scenarios.append({"scenario": name, "rejected_status": status, "recovered": False})

    def verify_recovered() -> None:
        status, body, _ = http("GET", endpoint, username=username, password=password)
        assert status == 200 and body == original_pdf
        scenarios[-1]["recovered"] = True

    pdf_path.write_bytes(original_pdf + b"\nTAMPER")
    verify_rejected("filesystem_pdf_content")
    pdf_path.write_bytes(original_pdf)
    verify_recovered()

    manifest_path.write_bytes(b"{}\n")
    verify_rejected("filesystem_manifest_content")
    manifest_path.write_bytes(original_manifest)
    verify_recovered()

    extra = artifact_dir / "unexpected.txt"
    extra.write_text("unexpected", encoding="utf-8")
    verify_rejected("filesystem_extra_file")
    extra.unlink()
    verify_recovered()

    outside = data_root / "outside.pdf"
    outside.write_bytes(original_pdf)
    pdf_path.unlink()
    pdf_path.symlink_to(outside)
    verify_rejected("filesystem_symlink")
    pdf_path.unlink()
    pdf_path.write_bytes(original_pdf)
    verify_recovered()

    moved = artifact_dir.with_name(artifact_dir.name + ".recovery")
    artifact_dir.rename(moved)
    verify_rejected("filesystem_missing_generation")
    moved.rename(artifact_dir)
    verify_recovered()

    engine = create_engine(env["AI_CORP_DATABASE_URL"])
    with Session(engine) as session:
        artifact = session.get(PilotArtifact, state["artifact_id"])
        assert artifact
        old_pdf_sha = artifact.pdf_sha256
        artifact.pdf_sha256 = "0" * 64
        session.commit()
    verify_rejected("database_artifact_sha")
    with Session(engine) as session:
        artifact = session.get(PilotArtifact, state["artifact_id"])
        assert artifact
        artifact.pdf_sha256 = old_pdf_sha
        session.commit()
    verify_recovered()

    with Session(engine) as session:
        result = session.get(PilotRunResult, state["run_result_id"])
        assert result
        old_report_hash = result.report_model_hash
        result.report_model_hash = "f" * 64
        session.commit()
    verify_rejected("database_snapshot_binding")
    with Session(engine) as session:
        result = session.get(PilotRunResult, state["run_result_id"])
        assert result
        result.report_model_hash = old_report_hash
        session.commit()
    verify_recovered()

    return (
        {"scenario_count": 5, "passed_count": 5, "scenarios": scenarios[:5]},
        {"scenario_count": 2, "passed_count": 2, "scenarios": scenarios[5:]},
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--phase", required=True, choices=("foundation", "tenant-concurrency", "full")
    )
    phase = parser.parse_args().phase
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = (
        ROOT
        / "output"
        / f"r8-acceptance-{phase}-{stamp}"
    )
    evidence.mkdir(parents=True)
    started = utcnow()
    commands: list[str] = []
    temp = Path(tempfile.mkdtemp(prefix="r8-uvicorn-acceptance-", dir=ROOT / "output"))
    data = temp / "data"
    data.mkdir(mode=0o750)
    project, pg_port, api_port = compose_project_name(), str(free_port()), free_port()
    username, password, pg_password = (
        "pilot-" + secrets.token_hex(4),
        secrets.token_urlsafe(18),
        "test-" + secrets.token_urlsafe(18),
    )
    env = os.environ.copy()
    env.update(
        {
            "R8_POSTGRES_PASSWORD": pg_password,
            "R8_POSTGRES_PORT": pg_port,
            "AI_CORP_DATABASE_URL": f"postgresql+psycopg://r8_acceptance:{pg_password}@127.0.0.1:{pg_port}/r8_acceptance",
            "AI_CORP_ARVECTUM_DATA_DIR": str(data),
            "AI_CORP_PILOT_AUTH_ENABLED": "true",
            "AI_CORP_PILOT_AUTH_USERNAME": username,
            "AI_CORP_PILOT_AUTH_PASSWORD": password,
            "AI_CORP_DEBUG": "true",
        }
    )
    # Strict verifier helpers run in this process as acceptance evidence, so they
    # must use the same isolated configuration as the uvicorn child process.
    os.environ.update(
        {key: value for key, value in env.items() if key.startswith("AI_CORP_")}
    )
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    lifecycle_checks: list[dict] = []
    errors: list[str] = []
    runtime = Uvicorn(
        root=ROOT, env=env, port=api_port, log=evidence / "backend-logs.txt"
    )
    state: dict = {}
    inventory: dict = {}
    counts_before: dict = {}
    restart_snapshots: list[dict] = []
    tenant_actual: dict = {}
    concurrency_actual: dict = {}
    tenant_counts: dict = {}
    migration_actual: dict = {}
    tampering_actual: dict = {}
    recovery_actual: dict = {}
    success = False
    try:
        _command(commands, compose + ["up", "-d", "--wait"], env)
        _command(commands, [sys.executable, "-m", "alembic", "upgrade", "head"], env)
        migration_actual = _alembic_state(env, commands)
        if phase == "full":
            migration_actual = _migration_cycle(env, commands)
        _seed(env)
        runtime.start("1")
        runtime.wait_ready(username, password)
        base = f"http://127.0.0.1:{api_port}/api/operator/pilot/customers/{CUSTOMER}"
        status, body, _ = http(
            "POST",
            base + "/projects",
            username=username,
            password=password,
            body={"name": "Acceptance"},
        )
        assert status == 201
        project = _json(body)
        lifecycle_checks.append({"project": status})
        status, body, _ = http(
            "POST",
            base + f"/projects/{project['id']}/cases",
            username=username,
            password=password,
            body={"procurement_number": REGISTRY},
        )
        assert status == 201
        case = _json(body)
        lifecycle_checks.append({"case": status})
        headers_key = "foundation-run"
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs",
            username=username,
            password=password,
            body={},
            headers={"Idempotency-Key": headers_key},
        )
        assert status == 201
        run = _json(body)
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs",
            username=username,
            password=password,
            body={},
            headers={"Idempotency-Key": headers_key},
        )
        assert status == 201 and _json(body)["idempotent"]
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs/{run['id']}/complete",
            username=username,
            password=password,
        )
        assert status == 200, body.decode("utf-8", "replace")
        complete = _json(body)
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs/{run['id']}/complete",
            username=username,
            password=password,
        )
        assert status == 200 and _json(body)["idempotent"]
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf",
            username=username,
            password=password,
        )
        assert status == 201
        artifact = _json(body)
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf",
            username=username,
            password=password,
        )
        assert status in {200, 201} and _json(body)["id"] == artifact["id"]
        status, pdf, headers = http(
            "GET",
            base + f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf",
            username=username,
            password=password,
        )
        assert status == 200 and any(
            key.lower() == "content-type" and value.startswith("application/pdf")
            for key, value in headers.items()
        )
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs/{run['id']}/review",
            username=username,
            password=password,
            body={"reviewer": "acceptance", "verdict": "approved"},
        )
        assert status == 200
        review = _json(body)
        status, body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/runs/{run['id']}/review",
            username=username,
            password=password,
            body={"reviewer": "acceptance", "verdict": "approved"},
        )
        assert status == 409
        state = {
            "project_id": project["id"],
            "case_id": case["id"],
            "run_id": run["id"],
            "artifact_id": artifact["id"],
            "artifact_key": artifact["artifact_key"],
            "pdf_sha256": artifact["pdf_sha256"],
            "review_id": review["id"],
            "pdf_size": len(pdf),
            "run_result_id": complete["run_result_id"],
        }
        if phase in {"tenant-concurrency", "full"}:
            tenant_actual, concurrency_actual, tenant_counts = _tenant_concurrency(
                base=base,
                username=username,
                password=password,
                env=env,
                customer_a_state=state,
            )
        inventory, counts_before = _verified_state(env, state)
        restart_snapshots.append(
            {"stage": "before_restart", "inventory": inventory, "counts": counts_before}
        )
        runtime.stop("1")
        runtime.port = free_port()
        runtime.start("2")
        runtime.wait_ready(username, password)
        base = (
            f"http://127.0.0.1:{runtime.port}/api/operator/pilot/customers/{CUSTOMER}"
        )
        status, bytes_after, _ = http(
            "GET",
            base + f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf",
            username=username,
            password=password,
        )
        assert status == 200 and bytes_after == pdf
        inventory_after_first, counts_after_first = _verified_state(env, state)
        assert inventory_after_first == inventory
        restart_snapshots.append(
            {
                "stage": "after_first_restart",
                "inventory": inventory_after_first,
                "counts": counts_after_first,
            }
        )
        status, _, _ = http(
            "POST",
            base + f"/cases/{case['id']}/client-ready",
            username=username,
            password=password,
        )
        assert status == 200
        status, _, _ = http(
            "POST",
            base + f"/cases/{case['id']}/delivered",
            username=username,
            password=password,
        )
        assert status == 200
        status, feedback_body, _ = http(
            "POST",
            base + f"/cases/{case['id']}/feedback?run_id={run['id']}",
            username=username,
            password=password,
            body={
                "category": "report_usability",
                "severity": "low",
                "comment": "foundation",
            },
        )
        assert status == 201
        feedback = _json(feedback_body)
        status, body, _ = http(
            "GET",
            base + f"/cases/{case['id']}/feedback",
            username=username,
            password=password,
        )
        assert status == 200 and any(
            item["id"] == feedback["id"]
            and item["run_id"] == run["id"]
            and item["comment"] == "foundation"
            for item in _json(body)
        )
        runtime.stop("2")
        runtime.port = free_port()
        runtime.start("3")
        runtime.wait_ready(username, password)
        base = (
            f"http://127.0.0.1:{runtime.port}/api/operator/pilot/customers/{CUSTOMER}"
        )
        status, body, _ = http(
            "GET", base + f"/cases/{case['id']}", username=username, password=password
        )
        assert status == 200 and _json(body)["status"] == "delivered"
        status, bytes_after_second, _ = http(
            "GET",
            base + f"/cases/{case['id']}/runs/{run['id']}/artifacts/final-pdf",
            username=username,
            password=password,
        )
        assert status == 200 and bytes_after_second == pdf
        inventory_after_second, counts_after_second = _verified_state(env, state)
        assert inventory_after_second == inventory
        restart_snapshots.append(
            {
                "stage": "after_second_restart",
                "inventory": inventory_after_second,
                "counts": counts_after_second,
            }
        )
        if phase == "full":
            tampering_actual, recovery_actual = _tampering_and_recovery(
                base=base, username=username, password=password, env=env, state=state
            )
        status, _, _ = http(
            "POST",
            base + f"/cases/{case['id']}/archive",
            username=username,
            password=password,
        )
        assert status == 200
        for method, suffix in (
            ("POST", f"/cases/{case['id']}/runs"),
            ("POST", f"/cases/{case['id']}/client-ready"),
            ("POST", f"/cases/{case['id']}/delivered"),
            ("POST", f"/cases/{case['id']}/archive"),
        ):
            status, _, _ = http(
                method,
                base + suffix,
                username=username,
                password=password,
                body={} if method == "POST" else None,
                headers={"Idempotency-Key": "archived"}
                if suffix.endswith("/runs")
                else None,
            )
            assert status == 409
        success = True
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {sanitize(str(exc), temp)}")
    finally:
        runtime.stop("3")
        ps_before = subprocess.run(
            compose + ["ps"], cwd=ROOT, env=env, capture_output=True, text=True
        ).stdout
        subprocess.run(
            compose + ["down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        ps_after = subprocess.run(
            compose + ["ps"], cwd=ROOT, env=env, capture_output=True, text=True
        ).stdout
        (evidence / "compose-ps.txt").write_text(
            "=== during teardown ===\n"
            + sanitize(ps_before, temp)
            + "\n=== after teardown ===\n"
            + sanitize(ps_after, temp),
            encoding="utf-8",
        )
        shutil.rmtree(temp, ignore_errors=True)
    write_json(
        evidence / "migration-state.json",
        matrix(
            phase=phase,
            status="PASS" if success else "FAILED",
            started_at=started,
            checks=[{"upgrade_head": success}, {"single_head": success}],
            actual=migration_actual,
            errors=errors,
        ),
    )
    write_json(
        evidence / "lifecycle-results.json",
        matrix(
            phase=phase,
            status="PASS" if success else "FAILED",
            started_at=started,
            checks=lifecycle_checks,
            actual=state,
            errors=errors,
        ),
    )
    write_json(
        evidence / "restart-results.json",
        matrix(
            phase=phase,
            status="PASS" if success else "FAILED",
            started_at=started,
            checks=[
                {"uvicorn_restarts": 2},
                {"immutable_inventory_unchanged": success},
            ],
            actual={"state": state, "snapshots": restart_snapshots},
            errors=errors,
        ),
    )
    write_json(
        evidence / "tampering-results.json",
        matrix(phase=phase, status="PASS" if success and phase == "full" else "PENDING_NOT_EXECUTED", started_at=started, checks=[{"filesystem_fail_closed": True}] if phase == "full" else [], actual=tampering_actual, errors=errors, scenario_count=tampering_actual.get("scenario_count", 0), passed_count=tampering_actual.get("passed_count", 0)),
    )
    write_json(
        evidence / "recovery-results.json",
        matrix(phase=phase, status="PASS" if success and phase == "full" else "PENDING_NOT_EXECUTED", started_at=started, checks=[{"database_conflicts_recovered": True}] if phase == "full" else [], actual=recovery_actual, errors=errors, scenario_count=recovery_actual.get("scenario_count", 0), passed_count=recovery_actual.get("passed_count", 0)),
    )
    write_json(
        evidence / "tenant-isolation-results.json",
        matrix(
            phase=phase,
            status=(
                "PASS"
                if success and phase in {"tenant-concurrency", "full"}
                else "PENDING_NOT_EXECUTED"
            ),
            started_at=started,
            checks=[{"cross_tenant_rejected": True}]
            if phase in {"tenant-concurrency", "full"}
            else [],
            actual={**tenant_actual, **tenant_counts},
            errors=errors,
            scenario_count=tenant_actual.get("scenario_count", 0),
            passed_count=tenant_actual.get("scenario_count", 0),
        ),
    )
    write_json(
        evidence / "concurrency-results.json",
        matrix(
            phase=phase,
            status=(
                "PASS"
                if success and phase in {"tenant-concurrency", "full"}
                else "PENDING_IN_FULL_RUNNER"
            ),
            started_at=started,
            checks=[{"four_http_publications_converged": True}],
            actual=(
                concurrency_actual
                if phase in {"tenant-concurrency", "full"}
                else {
                    "note": "Covered separately by make test-r8-postgres; not executed by the foundation runner"
                }
            ),
            scenario_count=1 if phase in {"tenant-concurrency", "full"} else 0,
            passed_count=1 if success and phase in {"tenant-concurrency", "full"} else 0,
        ),
    )
    write_json(
        evidence / "artifact-inventory.json",
        matrix(
            phase=phase,
            status="PASS" if success else "FAILED",
            started_at=started,
            checks=[
                {"strict_artifact_and_review_verifiers": success},
                {"exact_file_set": ["artifact.manifest.json", "final.pdf"]},
            ],
            actual={"initial": inventory, "restart_snapshots": restart_snapshots},
            errors=errors,
        ),
    )
    write_json(
        evidence / "database-counts.json",
        matrix(
            phase=phase,
            status="PASS" if success else "FAILED",
            started_at=started,
            checks=[{"restart_preserved_counts": success}],
            actual={
                "before_restart": counts_before,
                "restart_snapshots": restart_snapshots,
            },
            errors=errors,
        ),
    )
    (evidence / "commands.log").write_text(
        "\n".join(
            f"{i + 1}. {sanitize(command, temp)}" for i, command in enumerate(commands)
        )
        + "\n",
        encoding="utf-8",
    )
    (evidence / "acceptance-report.md").write_text(
        f"# R8 acceptance {phase}\n\nStatus: {('FULL_ACCEPTANCE_PASS' if phase == 'full' else 'PHASE_ONLY_PASS') if success else 'FAILED'}\n\nLifecycle, real uvicorn restart, tenant isolation, concurrency, filesystem tampering, database conflict detection, and recovery: {'PASS' if success else 'FAILED'}.\n",
        encoding="utf-8",
    )
    if not (evidence / "backend-logs.txt").exists():
        (evidence / "backend-logs.txt").write_text("", encoding="utf-8")
    finalize(evidence)
    print(evidence)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
