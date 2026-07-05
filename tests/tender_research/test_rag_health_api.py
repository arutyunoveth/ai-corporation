from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    @pytest.fixture()
    def _app(self):
        from src.main import app
        return app

    def test_health_returns_200(self, client: TestClient):
        resp = client.get("/api/tender-research/health")
        assert resp.status_code == 200

    def test_health_returns_expected_fields(self, client: TestClient):
        resp = client.get("/api/tender-research/health")
        body = resp.json()
        assert body["status"] == "ok"
        assert body["can_connect"] is True
        assert isinstance(body["database_url_masked"], str)
        assert "change_me_local_only" not in str(body).lower()
        assert "password" not in str(body).lower()
        assert isinstance(body["table_counts"], dict)
        assert "procurement_tenders" in body["table_counts"]
