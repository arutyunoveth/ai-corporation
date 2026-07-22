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
COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
REGISTRY = "0379100000726000101"
CUSTOMER = "R8-ACCEPTANCE-A"


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


def _verified_state(env: dict[str, str], state: dict) -> tuple[dict, dict]:
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
            CUSTOMER: {
                name: session.scalar(
                    select(func.count())
                    .select_from(model)
                    .where(model.customer_id == CUSTOMER)
                )
                for name, model in tables.items()
                if hasattr(model, "customer_id")
            }
        }
        return inventory, counts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", required=True, choices=("foundation",))
    parser.parse_args()
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "output" / f"r8-acceptance-foundation-{stamp}"
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
    success = False
    try:
        _command(commands, compose + ["up", "-d", "--wait"], env)
        _command(commands, [sys.executable, "-m", "alembic", "upgrade", "head"], env)
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
        status, _, _ = http(
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
        status, _, _ = http(
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
        status, _, _ = http(
            "POST",
            base + f"/cases/{case['id']}/archive",
            username=username,
            password=password,
        )
        assert status == 200
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
    pending = matrix(
        status="PENDING_NOT_EXECUTED",
        started_at=started,
        checks=[],
        actual={"note": "Reserved for full acceptance matrix"},
    )
    write_json(
        evidence / "migration-state.json",
        matrix(
            status="PASS" if success else "FAILED",
            started_at=started,
            checks=[{"upgrade_head": success}, {"single_head": success}],
        ),
    )
    write_json(
        evidence / "lifecycle-results.json",
        matrix(
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
    for name in (
        "tenant-isolation-results.json",
        "tampering-results.json",
        "recovery-results.json",
    ):
        write_json(evidence / name, pending)
    write_json(
        evidence / "concurrency-results.json",
        matrix(
            status="PENDING_IN_FULL_RUNNER",
            started_at=started,
            checks=[],
            actual={
                "note": "Covered separately by make test-r8-postgres; not executed by the foundation runner"
            },
        ),
    )
    write_json(
        evidence / "artifact-inventory.json",
        matrix(
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
        f"# R8 acceptance foundation\n\nStatus: {'FOUNDATION_ONLY' if success else 'FAILED'}\n\nNOT A FULL ACCEPTANCE CERTIFICATE.\n\nLifecycle and real uvicorn restart: {'PASS' if success else 'FAILED'}.\n",
        encoding="utf-8",
    )
    if not (evidence / "backend-logs.txt").exists():
        (evidence / "backend-logs.txt").write_text("", encoding="utf-8")
    finalize(evidence)
    print(evidence)
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
