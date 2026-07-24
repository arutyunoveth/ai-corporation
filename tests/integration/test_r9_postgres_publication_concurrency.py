"""Fail-closed PostgreSQL race: different first-publication bytes conflict."""

from __future__ import annotations

import hashlib
import os
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from test_r8_postgres_artifact_concurrency import _seed_intake


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_R8_POSTGRES_INTEGRATION") != "1",
    reason="requires scripts/acceptance/run_r8_postgres_tests.py",
)


def test_postgres_different_first_publication_bytes_fail_closed(tmp_path, monkeypatch):
    from src.main import app
    from src.modules.customer_pilot import (
        artifact_publisher,
        artifacts,
        canonical_snapshot,
    )
    from src.modules.customer_pilot.artifacts import verified_pilot_artifact
    from src.modules.customer_pilot.models import (
        PilotArtifact,
        PilotAuditEvent,
        PilotRunResult,
        ProcurementCase,
    )
    from src.modules.tender_operator_agent_demo import report_export_service
    from src.shared.db.session import SessionLocal
    from src.tender_research.models import TenderAnalysisRun

    config = lambda: type("Config", (), {"data_dir": str(tmp_path)})()
    monkeypatch.setattr(artifact_publisher, "load_config", config)
    monkeypatch.setattr(artifacts, "load_config", config)
    monkeypatch.setattr(canonical_snapshot, "load_config", config)
    customer = "R9-PG"
    registry = "0379100000726000102"
    with SessionLocal() as session:
        _seed_intake(session, customer, registry)
    with TestClient(app) as client:
        project = client.post(
            f"/api/operator/pilot/customers/{customer}/projects",
            json={"name": "R9 different"},
        )
        assert project.status_code == 201
        case = client.post(
            f"/api/operator/pilot/customers/{customer}/projects/{project.json()['id']}/cases",
            json={"procurement_number": registry},
        )
        assert case.status_code == 201
        case_id = case.json()["id"]
        run = client.post(
            f"/api/operator/pilot/customers/{customer}/cases/{case_id}/runs",
            json={},
            headers={"Idempotency-Key": "r9-different"},
        )
        assert run.status_code == 201
        run_id = run.json()["id"]
        assert (
            client.post(
                f"/api/operator/pilot/customers/{customer}/cases/{case_id}/runs/{run_id}/complete"
            ).status_code
            == 200
        )
    endpoint = f"/api/operator/pilot/customers/{customer}/cases/{case_id}/runs/{run_id}/artifacts/final-pdf"
    candidates = (
        b"%PDF-1.4\nR9-DIFFERENT-BYTE-A\n%%EOF\n",
        b"%PDF-1.4\nR9-DIFFERENT-BYTE-B\n%%EOF\n",
    )
    assert len(candidates[0]) == len(candidates[1])
    assert (
        hashlib.sha256(candidates[0]).hexdigest()
        != hashlib.sha256(candidates[1]).hexdigest()
    )
    barrier, lock, entries = threading.Barrier(2), threading.Lock(), []

    def render(_canonical, _title, output):
        with lock:
            index = len(entries)
            entries.append(index)
        barrier.wait(timeout=10)
        output.write_bytes(candidates[index])

    monkeypatch.setattr(report_export_service, "_build_pdf_from_canonical", render)

    def publish():
        with TestClient(app) as request_client:
            response = request_client.post(endpoint)
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: publish(), range(2)))
    statuses = [status for status, _ in results]
    assert entries == [0, 1]
    assert sorted(statuses) == [201, 409]
    assert all(status < 500 for status in statuses)
    success = next(payload for status, payload in results if status == 201)
    conflict = next(payload for status, payload in results if status == 409)
    assert "id" not in conflict and set(conflict) == {"detail"}
    assert not any(
        value in str(conflict) for value in (str(tmp_path), "postgres", "traceback")
    )
    with SessionLocal() as session:
        artifact = session.scalar(
            select(PilotArtifact).where(PilotArtifact.run_id == run_id)
        )
        assert artifact and artifact.id == success["id"]
        assert (
            session.scalar(
                select(func.count())
                .select_from(PilotRunResult)
                .where(PilotRunResult.run_id == run_id)
            )
            == 1
        )
        assert (
            session.scalar(
                select(func.count())
                .select_from(PilotAuditEvent)
                .where(
                    PilotAuditEvent.run_id == run_id,
                    PilotAuditEvent.event_type == "artifact_exported",
                )
            )
            == 1
        )
        run_row = session.get(TenderAnalysisRun, run_id)
        case_row = session.get(ProcurementCase, case_id)
        binding = session.scalar(
            select(PilotRunResult).where(PilotRunResult.run_id == run_id)
        )
        generation = verified_pilot_artifact(
            run_row, case_row, binding, artifact
        ).generation
        persisted = hashlib.sha256(generation.pdf_path.read_bytes()).hexdigest()
        hashes = {hashlib.sha256(value).hexdigest() for value in candidates}
        assert (
            persisted in hashes
            and artifact.pdf_sha256 == persisted
            and generation.parsed_manifest["pdf_sha256"] == persisted
        )
        assert {item.name for item in generation.artifact_directory.iterdir()} == {
            "final.pdf",
            "artifact.manifest.json",
        }
        assert not any(
            ".partial." in str(path)
            for path in generation.artifact_directory.parent.rglob("*")
        )
        before = (
            generation.pdf_path.stat().st_mtime_ns,
            generation.manifest_path.stat().st_mtime_ns,
        )
    with TestClient(app) as client:
        replay = client.post(endpoint)
    assert replay.status_code == 201 and replay.json()["id"] == success["id"]
    assert entries == [0, 1]
    assert (
        generation.pdf_path.stat().st_mtime_ns,
        generation.manifest_path.stat().st_mtime_ns,
    ) == before
