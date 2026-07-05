from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app

client = TestClient(app)


class _MockHistoryRecord:
    def __init__(
        self,
        *,
        run_id: str = "run-001",
        registry_number: str = "0323100010326000013",
        status: str = "completed",
        report_path: str | None = "data/rag/reports/analyze_tender_0323100010326000013.md",
        preview: str | None = "# Анализ закупки 0323100010326000013",
    ) -> None:
        self.id = run_id
        self.registry_number = registry_number
        self.status = status
        self.used_llm = True
        self.sections_count = 10
        self.sources_count = 30
        self.report_path = report_path
        self.report_markdown_preview = preview
        self.warnings = []
        self.errors = []
        self.duration_seconds = 12.5
        self.source = "api"
        self.created_at = "2026-07-05T20:00:00+00:00"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "registry_number": self.registry_number,
            "status": self.status,
            "used_llm": self.used_llm,
            "sections_count": self.sections_count,
            "sources_count": self.sources_count,
            "report_path": self.report_path,
            "preview": self.report_markdown_preview,
            "warnings": self.warnings,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
            "source": self.source,
            "created_at": self.created_at,
        }


class TestAnalysisHistoryApi:
    def test_list_history_returns_items(self) -> None:
        with patch(
            "src.tender_research.api.list_analysis_runs",
            return_value=([_MockHistoryRecord(), _MockHistoryRecord(run_id="run-002")], 2),
        ):
            response = client.get("/api/tender-research/analyze/history?limit=5")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["limit"] == 5
        assert len(data["items"]) == 2
        assert data["items"][0]["id"] == "run-001"
        assert data["items"][0]["registry_number"] == "0323100010326000013"
        assert "secret" not in response.text.lower()

    def test_list_history_passes_registry_number_filter(self) -> None:
        captured: dict[str, object] = {}

        def fake_list(session, *, registry_number=None, status=None, limit=20, offset=0):
            captured["registry_number"] = registry_number
            captured["status"] = status
            captured["limit"] = limit
            captured["offset"] = offset
            return ([_MockHistoryRecord(registry_number=str(registry_number))], 1)

        with patch("src.tender_research.api.list_analysis_runs", side_effect=fake_list):
            response = client.get(
                "/api/tender-research/analyze/history",
                params={"registry_number": "0323100010326000013", "limit": 3, "offset": 1},
            )

        assert response.status_code == 200
        assert captured == {
            "registry_number": "0323100010326000013",
            "status": None,
            "limit": 3,
            "offset": 1,
        }
        assert response.json()["items"][0]["registry_number"] == "0323100010326000013"

    def test_get_history_run_returns_details(self) -> None:
        with patch(
            "src.tender_research.api.get_analysis_run",
            return_value=_MockHistoryRecord(run_id="run-detail"),
        ):
            response = client.get("/api/tender-research/analyze/history/run-detail")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "run-detail"
        assert data["status"] == "completed"
        assert data["sections_count"] == 10
        assert "database_url" not in response.text.lower()

    def test_get_history_report_returns_markdown(self, tmp_path: Path) -> None:
        with patch("src.tender_research.api.load_config") as mock_load_config, patch(
            "src.tender_research.api.get_analysis_run_report",
            return_value=(
                _MockHistoryRecord(run_id="run-report"),
                "# Анализ закупки 0323100010326000013\n\nИстория доступна.",
                None,
            ),
        ):
            mock_load_config.return_value.data_dir = str(tmp_path)
            response = client.get("/api/tender-research/analyze/history/run-report/report")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "run-report"
        assert data["registry_number"] == "0323100010326000013"
        assert "История доступна." in data["report_markdown"]

    def test_missing_history_run_returns_404(self) -> None:
        with patch("src.tender_research.api.get_analysis_run", return_value=None):
            response = client.get("/api/tender-research/analyze/history/run-missing")

        assert response.status_code == 404
        assert response.json()["detail"] == "Analysis run not found"

    def test_missing_report_returns_clear_error(self, tmp_path: Path) -> None:
        with patch("src.tender_research.api.load_config") as mock_load_config, patch(
            "src.tender_research.api.get_analysis_run_report",
            return_value=(
                _MockHistoryRecord(run_id="run-missing-report"),
                None,
                "Report file is missing or inaccessible",
            ),
        ):
            mock_load_config.return_value.data_dir = str(tmp_path)
            response = client.get("/api/tender-research/analyze/history/run-missing-report/report")

        assert response.status_code == 404
        assert response.json()["detail"] == "Report file is missing or inaccessible"

    def test_missing_report_file_does_not_leak_secrets(self, tmp_path: Path) -> None:
        with patch("src.tender_research.api.load_config") as mock_load_config, patch(
            "src.tender_research.api.get_analysis_run_report",
            return_value=(
                _MockHistoryRecord(report_path="data/rag/reports/analyze_tender_secret.md"),
                None,
                "Report file is missing or inaccessible",
            ),
        ):
            mock_load_config.return_value.data_dir = str(tmp_path)
            response = client.get("/api/tender-research/analyze/history/run-secret/report")

        assert response.status_code == 404
        assert "password" not in response.text.lower()
        assert "token" not in response.text.lower()
        assert "postgresql+psycopg://" not in response.text.lower()

    def test_report_endpoint_uses_run_id_not_path_input(self) -> None:
        with patch("src.tender_research.api.get_analysis_run_report", return_value=(None, None, "Run not found")):
            response = client.get("/api/tender-research/analyze/history/../../../etc/passwd/report")

        assert response.status_code in (404, 422)

