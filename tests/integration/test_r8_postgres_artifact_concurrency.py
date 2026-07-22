from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select


pytestmark = pytest.mark.skipif(
    os.environ.get("RUN_R8_POSTGRES_INTEGRATION") != "1",
    reason="requires scripts/acceptance/run_r8_postgres_tests.py",
)


def _seed_intake(session) -> None:
    from src.modules.customer_registry.models import CustomerProfile
    from src.tender_research.models import (
        ProcurementDocumentChunk,
        ProcurementTender,
        ProcurementTenderDocument,
    )

    session.add(CustomerProfile(customer_id="R8-PG", legal_name="R8 PG", customer_status="prospect"))
    tender = ProcurementTender(
        source="r8-postgres-test", external_id="0379100000726000101",
        registry_number="0379100000726000101", title="Кабельная продукция",
    )
    session.add(tender)
    session.flush()
    document = ProcurementTenderDocument(
        tender_id=tender.id, file_name="Техническое задание.txt",
        download_status="downloaded", text_extraction_status="completed", sha256="a" * 64,
    )
    session.add(document)
    session.flush()
    session.add(ProcurementDocumentChunk(
        tender_id=tender.id, document_id=document.id, chunk_index=0,
        text="Поставка кабеля ВВГнг 3х2.5. Количество 100 метров. Срок 10 дней.",
        text_hash="b" * 64, char_start=0, char_end=70, token_estimate=16,
        source_file_name=document.file_name,
    ))
    session.commit()


def test_postgres_fastapi_concurrent_final_pdf_has_one_immutable_generation(tmp_path, monkeypatch):
    """Two independent TestClient request boundaries exercise real PG sessions."""
    from src.main import app
    from src.modules.customer_pilot.models import PilotArtifact, PilotRunResult, ProcurementCase
    from src.modules.customer_pilot.artifacts import verified_pilot_artifact
    from src.modules.customer_pilot import canonical_snapshot
    from src.shared.db.session import SessionLocal
    from src.tender_research.models import TenderAnalysisRun

    # The test owns this root independently of settings/cache initialization.
    monkeypatch.setattr(
        canonical_snapshot,
        "load_config",
        lambda: type("Config", (), {"data_dir": str(tmp_path)})(),
    )

    with SessionLocal() as session:
        _seed_intake(session)
    with TestClient(app) as client:
        project = client.post("/api/operator/pilot/customers/R8-PG/projects", json={"name": "PG"})
        assert project.status_code == 201
        case = client.post(
            f"/api/operator/pilot/customers/R8-PG/projects/{project.json()['id']}/cases",
            json={"procurement_number": "0379100000726000101"},
        )
        assert case.status_code == 201
        case_id = case.json()["id"]
        run = client.post(
            f"/api/operator/pilot/customers/R8-PG/cases/{case_id}/runs",
            json={}, headers={"Idempotency-Key": "pg-concurrency"},
        )
        assert run.status_code == 201
        run_id = run.json()["id"]
        complete = client.post(
            f"/api/operator/pilot/customers/R8-PG/cases/{case_id}/runs/{run_id}/complete"
        )
        assert complete.status_code == 200, complete.text

    endpoint = f"/api/operator/pilot/customers/R8-PG/cases/{case_id}/runs/{run_id}/artifacts/final-pdf"

    def publish() -> tuple[int, dict]:
        # Each client constructs its own HTTP request and gets a separate DB session.
        with TestClient(app) as request_client:
            response = request_client.post(endpoint)
            return response.status_code, response.json()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: publish(), range(2)))
    assert all(status < 500 for status, _ in results)
    assert {payload["id"] for _, payload in results}.__len__() == 1
    assert {payload["artifact_key"] for _, payload in results}.__len__() == 1
    assert {payload["pdf_sha256"] for _, payload in results}.__len__() == 1
    with SessionLocal() as session:
        artifacts = session.scalars(select(PilotArtifact)).all()
        assert len(artifacts) == 1
        result = session.scalar(select(PilotRunResult).where(PilotRunResult.run_id == run_id))
        run_row = session.scalar(select(TenderAnalysisRun).where(TenderAnalysisRun.id == run_id))
        case_row = session.scalar(select(ProcurementCase).where(ProcurementCase.id == case_id))
        verified_pilot_artifact(run_row, case_row, result, artifacts[0])
