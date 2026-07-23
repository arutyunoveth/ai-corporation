"""Real disposable PostgreSQL 095/096 legacy-backfill acceptance matrix."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
COMPOSE = ROOT / "tests/integration/compose.r8-postgres.yml"
FILES = (
    "acceptance-report.md",
    "commands.log",
    "migration-state.json",
    "legacy-fixtures.json",
    "backfill-results.json",
    "idempotency-results.json",
    "concurrency-results.json",
    "downgrade-results.json",
    "repeat-upgrade-results.json",
    "database-snapshots.json",
    "filesystem-snapshots.json",
    "compose-ps.txt",
    "backend-logs.txt",
    "SHA256SUMS",
)


def _port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def _sha(value):
    return hashlib.sha256(value).hexdigest()


def _jsonable(value):
    return value.isoformat() if hasattr(value, "isoformat") else value


def _write(path, payload):
    path.write_text(
        json.dumps(payload, default=_jsonable, sort_keys=True, indent=2) + "\n"
    )


def _command(args, env, commands, allow_fail=False):
    result = subprocess.run(args, cwd=ROOT, env=env, text=True, capture_output=True)
    commands.append(
        {
            "command": " ".join(args),
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:],
            "stderr": result.stderr[-2000:],
        }
    )
    if result.returncode and not allow_fail:
        raise RuntimeError(result.stdout + result.stderr)
    return result


def _revision(engine):
    return (
        engine.connect()
        .execute(text("SELECT version_num FROM alembic_version"))
        .scalar_one()
    )


def _schema(engine):
    inspector = inspect(engine)
    return {
        name: {
            "columns": sorted(item["name"] for item in inspector.get_columns(name)),
            "indexes": sorted(item["name"] for item in inspector.get_indexes(name)),
        }
        for name in ("pilot_run_results", "pilot_artifacts", "pilot_reviews")
    }


def _rows(engine):
    tables = (
        "pilot_projects",
        "procurement_cases",
        "tender_analysis_runs",
        "pilot_run_results",
        "pilot_artifacts",
        "pilot_reviews",
    )
    with engine.connect() as connection:
        return {
            table: [
                dict(row._mapping)
                for row in connection.execute(
                    text(f"SELECT * FROM {table} ORDER BY id")
                )
            ]
            for table in tables
        }


def _filesystem(root):
    result = {}
    for path in sorted(root.rglob("*")):
        stat = path.lstat()
        key = str(path.relative_to(root))
        if path.is_file():
            result[key] = {
                "type": "file",
                "size": stat.st_size,
                "sha256": _sha(path.read_bytes()),
                "mtime_ns": stat.st_mtime_ns,
            }
        elif path.is_dir():
            result[key] = {"type": "directory", "mtime_ns": stat.st_mtime_ns}
        else:
            result[key] = {"type": "special", "mtime_ns": stat.st_mtime_ns}
    return result


def _fixture(root, kind, ordinal):
    from src.modules.customer_pilot import canonical_snapshot
    from src.modules.customer_pilot.artifact_snapshot import (
        derive_final_pdf_artifact_identity,
        publish_final_pdf_generation,
    )
    from src.modules.procurement_analysis.frozen_producer import (
        produce_frozen_canonical_analysis,
    )

    ids = {
        key: str(uuid.uuid4())
        for key in (
            "project_id",
            "case_id",
            "run_id",
            "run_result_id",
            "artifact_id",
            "review_id",
        )
    }
    ids["customer_id"] = f"R8-LEGACY-{kind}-{ordinal}"
    ids["run_namespace_key"] = secrets.token_hex(12)
    ids["source_run_id"] = str(uuid.uuid4())
    canonical_snapshot.load_config = lambda: type(
        "Config", (), {"data_dir": str(root)}
    )()
    product = produce_frozen_canonical_analysis(
        registry_number="0379100000726000101",
        run_id=ids["run_id"],
        output_dir=root / "working" / kind,
        metadata={},
        documents=[],
        source_analysis_run_id=ids["source_run_id"],
    )
    published = canonical_snapshot.publish_canonical_snapshot(
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        procurement_case_id=ids["case_id"],
        run_id=ids["run_id"],
        registry_number="0379100000726000101",
        source_analysis_run_id=ids["source_run_id"],
        verified=product.persisted,
    )
    identity = derive_final_pdf_artifact_identity(
        registry_number="0379100000726000101",
        run_id=ids["run_id"],
        report_model_hash=product.persisted.report_model_hash,
        customer_id=ids["customer_id"],
        project_id=ids["project_id"],
        procurement_case_id=ids["case_id"],
    )
    from src.modules.tender_operator_agent_demo.report_export_service import (
        _build_pdf_from_canonical,
    )

    with tempfile.NamedTemporaryFile(suffix=".pdf") as rendered:
        _build_pdf_from_canonical(
            json.loads(product.persisted.canonical_report_bytes),
            "Legacy acceptance",
            Path(rendered.name),
        )
        generation = publish_final_pdf_generation(
            customer_id=ids["customer_id"],
            project_id=ids["project_id"],
            procurement_case_id=ids["case_id"],
            run_id=ids["run_id"],
            run_result_id=ids["run_result_id"],
            registry_number="0379100000726000101",
            source_analysis_run_id=ids["source_run_id"],
            run_namespace_key=ids["run_namespace_key"],
            artifact_key=identity.artifact_key,
            renderer_version=identity.renderer_version,
            requirements_storage_key=published.requirements_relative_path,
            requirements_file_sha256=published.requirements_file_sha256,
            canonical_report_storage_key=published.canonical_report_relative_path,
            canonical_report_file_sha256=published.canonical_report_file_sha256,
            binding_manifest_storage_key=published.binding_manifest_relative_path,
            binding_manifest_file_sha256=published.binding_manifest_file_sha256,
            source_graph_hash=published.source_graph_hash,
            source_graph_hash_algorithm=published.source_graph_hash_algorithm,
            production_model_hash=published.production_model_hash,
            report_model_hash=published.report_model_hash,
            pdf_bytes=Path(rendered.name).read_bytes(),
        )
    ids.update(
        {
            "type": kind,
            "artifact_key": identity.artifact_key,
            "canonical_report_storage_key": published.canonical_report_relative_path,
            "manifest_relative_path": generation.manifest_relative_path,
            "pdf_relative_path": generation.pdf_relative_path,
            "renderer_version": identity.renderer_version,
            "pdf_sha256": generation.pdf_sha256,
            "byte_size": generation.byte_size,
            "legacy_hash": product.persisted.report_model_hash,
            "source_graph_hash": product.persisted.source_graph_hash,
            "production_model_hash": product.persisted.production_model_hash,
        }
    )
    if kind == "INCOMPLETE":
        (published.analysis_directory / "canonical-binding.manifest.json").unlink()
    if kind == "CONFLICTING":
        ids["legacy_hash"] = "f" * 64
    if kind == "ARTIFACT_CONFLICTING":
        (root / generation.pdf_relative_path).write_bytes(b"%PDF-tampered")
    return ids


def _seed_095(engine, fixtures):
    now = datetime.now(UTC)
    with engine.begin() as connection:
        for item in fixtures:
            connection.execute(
                text(
                    "INSERT INTO customer_profiles (id,customer_id,legal_name,customer_status,created_at,updated_at) VALUES (:id,:customer_id,:legal_name,'prospect',:now,:now)"
                ),
                {
                    "id": str(uuid.uuid4()),
                    "customer_id": item["customer_id"],
                    "legal_name": item["customer_id"],
                    "now": now,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO pilot_projects (id,customer_id,name,internal_slug,created_at,updated_at) VALUES (:project_id,:customer_id,:name,:slug,:now,:now)"
                ),
                {
                    **item,
                    "name": item["type"],
                    "slug": item["type"].lower(),
                    "now": now,
                },
            )
            connection.execute(
                text(
                    "INSERT INTO procurement_cases (id,customer_id,project_id,procurement_number,status,artifact_key,current_run_id,created_at,updated_at) VALUES (:case_id,:customer_id,:project_id,'0379100000726000101','operator_review',:run_namespace_key,NULL,:now,:now)"
                ),
                {**item, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO tender_analysis_runs (id,registry_number,status,used_llm,sections_count,sources_count,created_at,updated_at,customer_id,project_id,procurement_case_id,idempotency_key,artifact_key) VALUES (:run_id,'0379100000726000101','completed',false,0,0,:now,:now,:customer_id,:project_id,:case_id,:run_id,:run_namespace_key)"
                ),
                {**item, "now": now},
            )
            connection.execute(
                text(
                    "UPDATE procurement_cases SET current_run_id=:run_id WHERE id=:case_id"
                ),
                item,
            )
            connection.execute(
                text(
                    "INSERT INTO pilot_run_results (id,customer_id,project_id,procurement_case_id,run_id,source_analysis_run_id,canonical_report_storage_key,canonical_report_hash,source_graph_hash,production_model_hash,created_at,completed_at) VALUES (:run_result_id,:customer_id,:project_id,:case_id,:run_id,:source_run_id,:canonical_report_storage_key,:legacy_hash,:source_graph_hash,:production_model_hash,:now,:now)"
                ),
                {**item, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO pilot_artifacts (id,customer_id,project_id,procurement_case_id,run_id,run_result_id,artifact_type,artifact_key,report_model_hash,source_graph_hash,renderer_version,manifest_relative_path,pdf_relative_path,pdf_sha256,byte_size,status,created_at,immutable_at) VALUES (:artifact_id,:customer_id,:project_id,:case_id,:run_id,:run_result_id,'final_pdf',:artifact_key,:legacy_hash,:source_graph_hash,:renderer_version,:manifest_relative_path,:pdf_relative_path,:pdf_sha256,:byte_size,'published',:now,:now)"
                ),
                {**item, "now": now},
            )
            connection.execute(
                text(
                    "INSERT INTO pilot_reviews (id,customer_id,project_id,procurement_case_id,run_id,artifact_id,artifact_key,pdf_sha256,renderer_version,reviewer,reviewed_at,verdict,checklist,source_graph_hash,report_model_hash,artifact_hashes,immutable_at) VALUES (:review_id,:customer_id,:project_id,:case_id,:run_id,:artifact_id,:artifact_key,:pdf_sha256,'legacy','acceptance',:now,'approved','{}'::jsonb,:source_graph_hash,:legacy_hash,'{}'::jsonb,:now)"
                ),
                {**item, "now": now},
            )


def _objects(session, ids):
    from src.shared.db import models as _models  # noqa: F401
    from src.modules.customer_pilot.models import (
        PilotArtifact,
        PilotRunResult,
        ProcurementCase,
    )
    from src.tender_research.models import TenderAnalysisRun

    return (
        session.get(TenderAnalysisRun, ids["run_id"]),
        session.get(ProcurementCase, ids["case_id"]),
        session.get(PilotRunResult, ids["run_result_id"]),
        session.get(PilotArtifact, ids["artifact_id"]),
    )


def _backfill(engine, ids, root):
    from src.modules.customer_pilot.legacy_binding_backfill import (
        backfill_legacy_run_binding,
    )
    from src.modules.customer_pilot.artifacts import verify_pilot_artifact_binding
    from src.modules.customer_pilot.binding_verifier import verify_run_snapshot_binding

    with Session(engine) as session:
        run, case, result, artifact = _objects(session, ids)
        before = {
            field: getattr(result, field) for field in result.__table__.columns.keys()
        }
        answer = backfill_legacy_run_binding(
            session=session,
            run=run,
            case=case,
            run_result=result,
            artifact=artifact,
            data_root=root,
        )
        canonical_verifier_status = "NOT_EXECUTED"
        artifact_verifier_status = "NOT_EXECUTED"
        if answer.status in {"BACKFILLED", "ALREADY_VERIFIED"}:
            verify_run_snapshot_binding(run=run, case=case, binding=result)
            canonical_verifier_status = "PASS"
            verify_pilot_artifact_binding(
                run=run, case=case, result=result, artifact=artifact
            )
            artifact_verifier_status = "PASS"
        session.commit()
        after = {
            field: getattr(result, field) for field in result.__table__.columns.keys()
        }
        return {
            "status": answer.status,
            "changed_fields": answer.changed_fields,
            "error_category": answer.error_category,
            "mutation_performed": answer.mutation_performed,
            "canonical_verifier_status": canonical_verifier_status,
            "artifact_verifier_status": artifact_verifier_status,
            "before": before,
            "after": after,
        }


def _finalize(root):
    expected = set(FILES) - {"SHA256SUMS"}
    actual = {item.name for item in root.iterdir() if item.is_file()}
    if actual != expected:
        raise RuntimeError(f"evidence files invalid: {sorted(actual)}")
    (root / "SHA256SUMS").write_text(
        "\n".join(
            f"{_sha((root / name).read_bytes())}  {name}" for name in sorted(expected)
        )
        + "\n"
    )


def main():
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    evidence = ROOT / "output" / f"r8-acceptance-migration-backfill-{stamp}"
    evidence.mkdir(parents=True)
    temp = Path(tempfile.mkdtemp(prefix="r8-migration-backfill-", dir=ROOT / "output"))
    data = temp / "data"
    data.mkdir()
    project = f"r8backfill{secrets.token_hex(4)}"
    port = str(_port())
    password = "test-" + secrets.token_urlsafe(18)
    commands = []
    env = os.environ.copy()
    env.update(
        {
            "R8_POSTGRES_PASSWORD": password,
            "R8_POSTGRES_PORT": port,
            "AI_CORP_DATABASE_URL": f"postgresql+psycopg://r8_acceptance:{password}@127.0.0.1:{port}/r8_acceptance",
            "AI_CORP_ARVECTUM_DATA_DIR": str(data),
        }
    )
    os.environ.update({"AI_CORP_ARVECTUM_DATA_DIR": str(data)})
    compose = ["docker", "compose", "-p", project, "-f", str(COMPOSE)]
    engine = create_engine(env["AI_CORP_DATABASE_URL"])
    scenarios = {}
    db = {}
    fs = {}
    fixtures = []
    cleanup = {}
    error = None
    try:
        _command(compose + ["up", "-d", "--wait"], env, commands)
        _command(
            [sys.executable, "-m", "alembic", "upgrade", "095_add_r8_current_run"],
            env,
            commands,
        )
        assert _revision(engine) == "095_add_r8_current_run"
        fixtures = [
            _fixture(data, kind, index)
            for index, kind in enumerate(
                (
                    "RECOVERABLE",
                    "INCOMPLETE",
                    "CONFLICTING",
                    "ARTIFACT_CONFLICTING",
                    "CONCURRENT",
                ),
                1,
            )
        ]
        _seed_095(engine, fixtures)
        db["before_upgrade"] = _rows(engine)
        fs["before_upgrade"] = _filesystem(data)
        _command(
            [
                sys.executable,
                "-m",
                "alembic",
                "upgrade",
                "096_add_r8_canonical_snapshot_binding",
            ],
            env,
            commands,
        )
        assert _revision(engine) == "096_add_r8_canonical_snapshot_binding"
        db["after_upgrade_before_backfill"] = _rows(engine)
        fs["after_upgrade_before_backfill"] = _filesystem(data)
        scenarios["recoverable"] = _backfill(engine, fixtures[0], data)
        scenarios["incomplete"] = _backfill(engine, fixtures[1], data)
        scenarios["conflicting"] = _backfill(engine, fixtures[2], data)
        scenarios["artifact_conflicting"] = _backfill(engine, fixtures[3], data)
        scenarios["idempotent"] = _backfill(engine, fixtures[0], data)
        barrier = threading.Barrier(2)

        def concurrent_call(_):
            barrier.wait()
            return _backfill(engine, fixtures[4], data)

        with ThreadPoolExecutor(max_workers=2) as pool:
            scenarios["concurrency"] = list(pool.map(concurrent_call, range(2)))
        db["after_backfill"] = _rows(engine)
        fs["after_backfill"] = _filesystem(data)
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE pilot_run_results SET canonical_report_hash=NULL, report_model_hash=NULL WHERE id=:id"
                ),
                {"id": fixtures[0]["run_result_id"]},
            )
        invalid = _command(
            [sys.executable, "-m", "alembic", "downgrade", "095_add_r8_current_run"],
            env,
            commands,
            True,
        )
        scenarios["invalid_downgrade"] = {
            "exit_code": invalid.returncode,
            "output": invalid.stdout + invalid.stderr,
            "revision_after": _revision(engine),
        }
        with engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE pilot_run_results SET canonical_report_hash=:hash, report_model_hash=:hash WHERE id=:id"
                ),
                {
                    "id": fixtures[0]["run_result_id"],
                    "hash": fixtures[0]["legacy_hash"],
                },
            )
        _command(
            [sys.executable, "-m", "alembic", "downgrade", "095_add_r8_current_run"],
            env,
            commands,
        )
        scenarios["downgrade"] = {"revision": _revision(engine), "rows": _rows(engine)}
        _command(
            [
                sys.executable,
                "-m",
                "alembic",
                "upgrade",
                "096_add_r8_canonical_snapshot_binding",
            ],
            env,
            commands,
        )
        scenarios["repeat_upgrade"] = {
            "revision": _revision(engine),
            "recoverable": _backfill(engine, fixtures[0], data),
            "idempotent": _backfill(engine, fixtures[0], data),
            "incomplete": _backfill(engine, fixtures[1], data),
            "conflicting": _backfill(engine, fixtures[2], data),
            "artifact_conflicting": _backfill(engine, fixtures[3], data),
        }
        assert (
            scenarios["recoverable"]["status"] == "BACKFILLED"
            and scenarios["idempotent"]["status"] == "ALREADY_VERIFIED"
            and scenarios["incomplete"]["status"] == "INCOMPLETE"
            and scenarios["conflicting"]["status"] == "CONFLICT"
            and scenarios["artifact_conflicting"]["status"] == "CONFLICT"
            and sorted(item["status"] for item in scenarios["concurrency"])
            == ["ALREADY_VERIFIED", "BACKFILLED"]
            and scenarios["invalid_downgrade"]["exit_code"] != 0
            and scenarios["invalid_downgrade"]["revision_after"]
            == "096_add_r8_canonical_snapshot_binding"
        )
    except Exception as exc:
        error = f"{type(exc).__name__}: {exc}"
    finally:
        engine.dispose()
        subprocess.run(
            compose + ["down", "--volumes", "--remove-orphans"],
            cwd=ROOT,
            env=env,
            capture_output=True,
        )
        shutil.rmtree(temp, ignore_errors=True)

        def ids(args):
            return (
                subprocess.run(args, capture_output=True, text=True)
                .stdout.strip()
                .splitlines()
            )

        cleanup = {
            "containers": ids(
                [
                    "docker",
                    "ps",
                    "-aq",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ]
            ),
            "volumes": ids(
                [
                    "docker",
                    "volume",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ]
            ),
            "networks": ids(
                [
                    "docker",
                    "network",
                    "ls",
                    "-q",
                    "--filter",
                    f"label=com.docker.compose.project={project}",
                ]
            ),
            "temp_root_removed": not temp.exists(),
        }
    sha = (
        os.environ.get("GITHUB_HEAD_SHA")
        or subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    )
    clean = (
        not error
        and not any(cleanup[key] for key in ("containers", "volumes", "networks"))
        and cleanup["temp_root_removed"]
    )
    _write(evidence / "legacy-fixtures.json", {"fixtures": fixtures})
    _write(
        evidence / "backfill-results.json",
        {
            key: scenarios.get(key)
            for key in (
                "recoverable",
                "incomplete",
                "conflicting",
                "artifact_conflicting",
            )
        },
    )
    _write(evidence / "idempotency-results.json", scenarios.get("idempotent", {}))
    _write(
        evidence / "concurrency-results.json",
        {"transactions": scenarios.get("concurrency", [])},
    )
    _write(
        evidence / "downgrade-results.json",
        {key: scenarios.get(key) for key in ("downgrade", "invalid_downgrade")},
    )
    _write(
        evidence / "repeat-upgrade-results.json", scenarios.get("repeat_upgrade", {})
    )
    _write(evidence / "database-snapshots.json", db)
    _write(evidence / "filesystem-snapshots.json", fs)
    _write(
        evidence / "migration-state.json",
        {
            "initial_revision": "095_add_r8_current_run",
            "post_upgrade_revision": "096_add_r8_canonical_snapshot_binding",
            "downgrade_revision": scenarios.get("downgrade", {}).get("revision"),
            "repeat_upgrade_revision": scenarios.get("repeat_upgrade", {}).get(
                "revision"
            ),
            "implementation_sha": sha,
            "head_sha": sha,
            "cleanup_status": "PASS" if clean else "FAILED",
            "error": error,
        },
    )
    (evidence / "commands.log").write_text(
        "\n".join(json.dumps(item) for item in commands) + "\n"
    )
    (evidence / "backend-logs.txt").write_text("")
    (evidence / "compose-ps.txt").write_text(json.dumps(cleanup, indent=2))
    status = (
        "R8_PRE096_MIGRATION_BACKFILL_VERIFIED_REMAINING_MATRICES_REQUIRED"
        if clean
        else "R8_PRE096_MIGRATION_BACKFILL_REVIEW_CHANGES_REQUIRED"
    )
    summary = {
        "recoverable": scenarios.get("recoverable", {}).get("status", "FAILED"),
        "idempotent": scenarios.get("idempotent", {}).get("status", "FAILED"),
        "incomplete": scenarios.get("incomplete", {}).get("status", "FAILED"),
        "conflicting": scenarios.get("conflicting", {}).get("status", "FAILED"),
        "artifact_conflicting": scenarios.get("artifact_conflicting", {}).get(
            "status", "FAILED"
        ),
        "concurrency": " + ".join(
            item.get("status", "FAILED") for item in scenarios.get("concurrency", [])
        ),
        "invalid_downgrade": "PASS"
        if scenarios.get("invalid_downgrade", {}).get("exit_code")
        else "FAILED",
        "normal_downgrade": "PASS"
        if scenarios.get("downgrade", {}).get("revision") == "095_add_r8_current_run"
        else "FAILED",
        "repeat_upgrade": "PASS"
        if scenarios.get("repeat_upgrade", {}).get("revision")
        == "096_add_r8_canonical_snapshot_binding"
        else "FAILED",
        "canonical_verifier": scenarios.get("recoverable", {}).get(
            "canonical_verifier_status", "FAILED"
        ),
        "artifact_verifier": scenarios.get("recoverable", {}).get(
            "artifact_verifier_status", "FAILED"
        ),
        "cleanup": "PASS" if clean else "FAILED",
    }
    (evidence / "acceptance-report.md").write_text(
        "# R8 migration backfill acceptance\n\n"
        f"Status: {status}\n\n"
        + "\n".join(f"{key}: {value}" for key, value in summary.items())
        + "\n\nNOT A FULL ACCEPTANCE CERTIFICATE\n"
    )
    _finalize(evidence)
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
