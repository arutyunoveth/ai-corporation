from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient


class TestPrepareEndpoint:
    @pytest.fixture()
    def _app(self):
        from src.main import app
        return app

    def test_prepare_returns_200(self, client: TestClient):
        with patch("src.tender_research.api.prepare_tender_for_analysis") as mock_prepare:
            mock_result = _mock_result(status="completed", ready_for_analysis=True)
            mock_prepare.return_value = mock_result
            resp = client.post(
                "/api/tender-research/prepare",
                json={"registry_number": "0323100010326000013"},
            )
        assert resp.status_code == 200

    def test_prepare_returns_completed(self, client: TestClient):
        with patch("src.tender_research.api.prepare_tender_for_analysis") as mock_prepare:
            mock_result = _mock_result(
                status="completed",
                ready_for_analysis=True,
                tender_found=True,
                documents_total=10,
                documents_downloaded=10,
                extracted_texts_total=5,
                chunks_total=50,
                embeddings_total=50,
                steps=[
                    ("check_tender_exists", "completed", "Tender found in database", ""),
                    ("download_documents", "skipped", "Already downloaded", ""),
                    ("build_chunks", "skipped", "Already exist", ""),
                    ("build_embeddings", "skipped", "Already exist", ""),
                    ("readiness_check", "completed", "Ready", ""),
                ],
                warnings=[],
                errors=[],
            )
            mock_prepare.return_value = mock_result
            resp = client.post(
                "/api/tender-research/prepare",
                json={
                    "registry_number": "0323100010326000013",
                    "rebuild_chunks": False,
                    "rebuild_embeddings": False,
                },
            )
        body = resp.json()
        assert body["status"] == "completed"
        assert body["ready_for_analysis"] is True
        assert body["registry_number"] == "0323100010326000013"
        assert len(body["steps"]) == 5
        assert body["chunks_total"] == 50
        assert body["embeddings_total"] == 50

    def test_prepare_no_tender(self, client: TestClient):
        with patch("src.tender_research.api.prepare_tender_for_analysis") as mock_prepare:
            mock_result = _mock_result(
                status="no_tender",
                ready_for_analysis=False,
                tender_found=False,
                errors=["Tender not found"],
                steps=[
                    ("check_tender_exists", "failed", "Could not ingest", ""),
                ],
            )
            mock_prepare.return_value = mock_result
            resp = client.post(
                "/api/tender-research/prepare",
                json={"registry_number": "0000000000000000"},
            )
        body = resp.json()
        assert body["status"] == "no_tender"
        assert body["ready_for_analysis"] is False
        assert len(body["errors"]) > 0

    def test_prepare_embedding_failure(self, client: TestClient):
        with patch("src.tender_research.api.prepare_tender_for_analysis") as mock_prepare:
            mock_result = _mock_result(
                status="completed_with_warnings",
                ready_for_analysis=False,
                warnings=["Embedding server unavailable"],
                errors=[],
                chunks_total=50,
                embeddings_total=0,
                steps=[
                    ("check_tender_exists", "completed", "Found", ""),
                    ("build_chunks", "completed", "Created 50 chunks", ""),
                    ("build_embeddings", "failed", "Embedding server unavailable", ""),
                    ("readiness_check", "warning", "No embeddings", ""),
                ],
            )
            mock_prepare.return_value = mock_result
            resp = client.post(
                "/api/tender-research/prepare",
                json={"registry_number": "0323100010326000013"},
            )
        body = resp.json()
        assert body["status"] == "completed_with_warnings"
        assert body["ready_for_analysis"] is False
        assert len(body["warnings"]) > 0
        assert body["chunks_total"] == 50
        assert body["embeddings_total"] == 0

    def test_prepare_errors_no_traceback(self, client: TestClient):
        with patch("src.tender_research.api.prepare_tender_for_analysis") as mock_prepare:
            mock_prepare.side_effect = RuntimeError("Internal server error")
            resp = client.post(
                "/api/tender-research/prepare",
                json={"registry_number": "0323100010326000013"},
            )
        assert resp.status_code == 500
        body = resp.json()
        assert "traceback" not in str(body).lower()
        assert "RuntimeError" not in str(body)

    def test_prepare_validation_error(self, client: TestClient):
        resp = client.post("/api/tender-research/prepare", json={})
        assert resp.status_code == 422

    def test_prepare_no_secrets_in_response(self, client: TestClient):
        with patch("src.tender_research.api.prepare_tender_for_analysis") as mock_prepare:
            mock_result = _mock_result(status="failed", errors=["error"])
            mock_prepare.return_value = mock_result
            resp = client.post(
                "/api/tender-research/prepare",
                json={"registry_number": "0323100010326000013"},
            )
        body_str = str(resp.json()).lower()
        assert "change_me_local_only" not in body_str
        assert "password" not in body_str

    def test_prepare_idempotent(self, client: TestClient):
        with patch("src.tender_research.api.prepare_tender_for_analysis") as mock_prepare:
            mock_result = _mock_result(status="completed", ready_for_analysis=True)
            mock_prepare.return_value = mock_result
            resp1 = client.post(
                "/api/tender-research/prepare",
                json={"registry_number": "0323100010326000013"},
            )
            resp2 = client.post(
                "/api/tender-research/prepare",
                json={"registry_number": "0323100010326000013"},
            )
        assert resp1.status_code == 200
        assert resp2.status_code == 200
        assert resp1.json()["status"] == resp2.json()["status"]


class TestPreparationStatusEndpoint:
    def test_status_returns_200(self, client: TestClient):
        with patch("src.tender_research.api.check_preparation_status") as mock_status:
            mock_status.return_value = {
                "registry_number": "0323100010326000013",
                "tender_found": True,
                "documents_total": 10,
                "documents_downloaded": 10,
                "extracted_texts_total": 5,
                "chunks_total": 50,
                "embeddings_total": 50,
                "ready_for_analysis": True,
                "missing": [],
            }
            resp = client.get("/api/tender-research/prepare/0323100010326000013/status")
        assert resp.status_code == 200

    def test_status_returns_ready(self, client: TestClient):
        with patch("src.tender_research.api.check_preparation_status") as mock_status:
            mock_status.return_value = {
                "registry_number": "0323100010326000013",
                "tender_found": True,
                "documents_total": 10,
                "documents_downloaded": 10,
                "extracted_texts_total": 5,
                "chunks_total": 50,
                "embeddings_total": 50,
                "ready_for_analysis": True,
                "missing": [],
            }
            resp = client.get("/api/tender-research/prepare/0323100010326000013/status")
        body = resp.json()
        assert body["ready_for_analysis"] is True
        assert body["tender_found"] is True
        assert body["chunks_total"] == 50
        assert body["embeddings_total"] == 50
        assert body["missing"] == []

    def test_status_not_ready(self, client: TestClient):
        with patch("src.tender_research.api.check_preparation_status") as mock_status:
            mock_status.return_value = {
                "registry_number": "0323100010326000013",
                "tender_found": True,
                "documents_total": 10,
                "documents_downloaded": 0,
                "extracted_texts_total": 0,
                "chunks_total": 0,
                "embeddings_total": 0,
                "ready_for_analysis": False,
                "missing": ["chunks", "embeddings"],
            }
            resp = client.get("/api/tender-research/prepare/0323100010326000013/status")
        body = resp.json()
        assert body["ready_for_analysis"] is False
        assert "chunks" in body["missing"]
        assert "embeddings" in body["missing"]

    def test_status_no_tender(self, client: TestClient):
        with patch("src.tender_research.api.check_preparation_status") as mock_status:
            mock_status.return_value = {
                "registry_number": "0000000000000000",
                "tender_found": False,
                "documents_total": 0,
                "documents_downloaded": 0,
                "extracted_texts_total": 0,
                "chunks_total": 0,
                "embeddings_total": 0,
                "ready_for_analysis": False,
                "missing": ["tender"],
            }
            resp = client.get("/api/tender-research/prepare/0000000000000000/status")
        body = resp.json()
        assert body["tender_found"] is False
        assert body["ready_for_analysis"] is False

    def test_status_invalid_registry_number(self, client: TestClient):
        resp = client.get("/api/tender-research/prepare/abc/status")
        assert resp.status_code == 400

    def test_status_no_secrets(self, client: TestClient):
        with patch("src.tender_research.api.check_preparation_status") as mock_status:
            mock_status.return_value = {
                "registry_number": "0323100010326000013",
                "tender_found": True,
                "documents_total": 0,
                "documents_downloaded": 0,
                "extracted_texts_total": 0,
                "chunks_total": 0,
                "embeddings_total": 0,
                "ready_for_analysis": False,
                "missing": ["tender"],
            }
            resp = client.get("/api/tender-research/prepare/0323100010326000013/status")
        body_str = str(resp.json()).lower()
        assert "change_me_local_only" not in body_str
        assert "password" not in body_str


def _mock_result(
    status="completed",
    ready_for_analysis=False,
    tender_found=False,
    documents_total=0,
    documents_downloaded=0,
    extracted_texts_total=0,
    chunks_total=0,
    chunks_created=0,
    embeddings_total=0,
    embeddings_created=0,
    steps=None,
    warnings=None,
    errors=None,
    registry_number="0323100010326000013",
    tender_id=None,
):
    from src.tender_research.rag.prepare_service import TenderPreparationResult, TenderPreparationStep

    step_objs = []
    if steps:
        for s in steps:
            name, st, msg, det = s if len(s) == 4 else (s[0], s[1], s[2], "")
            step_objs.append(TenderPreparationStep(name, st, msg, det))

    return TenderPreparationResult(
        status=status,
        registry_number=registry_number,
        ready_for_analysis=ready_for_analysis,
        steps=step_objs,
        tender_found=tender_found,
        documents_total=documents_total,
        documents_downloaded=documents_downloaded,
        extracted_texts_total=extracted_texts_total,
        chunks_total=chunks_total,
        chunks_created=chunks_created,
        embeddings_total=embeddings_total,
        embeddings_created=embeddings_created,
        warnings=warnings or [],
        errors=errors or [],
        tender_id=tender_id,
    )
