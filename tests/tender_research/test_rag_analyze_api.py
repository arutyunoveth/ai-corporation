from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.tender_research.rag.schemas import TenderAnalysisResult, TenderAnalysisSection

client = TestClient(app)


class TestAnalyzeEndpoint:
    def test_analyze_missing_registry_number(self):
        """POST /api/tender-research/analyze with missing registry_number."""
        response = client.post("/api/tender-research/analyze", json={})
        assert response.status_code == 422

    def test_analyze_success(self):
        """POST /api/tender-research/analyze returns structured response."""
        mock_section = TenderAnalysisSection(
            id="01_notice_info",
            title="Информация об извещении",
            question="Тестовый вопрос",
            answer="Тестовый ответ",
            sources=[],
            status="completed",
        )
        mock_result = TenderAnalysisResult(
            status="completed",
            registry_number="0323100010326000013",
            sections=[mock_section],
            sections_count=1,
            sources_count=5,
            analysis_mode="fast",
            report_markdown="# Test Report",
            used_llm=False,
            duration_seconds=4.2,
            timings={"total_seconds": 4.2},
            warnings=[],
            errors=[],
        )

        with patch(
            "src.tender_research.api.analyze_tender",
            return_value=mock_result,
        ):
            response = client.post(
                "/api/tender-research/analyze",
                json={
                    "registry_number": "0323100010326000013",
                    "use_llm": False,
                    "save_report": False,
                    "limit": 6,
                },
            )
            assert response.status_code == 200
            data = response.json()
            assert data["registry_number"] == "0323100010326000013"
            assert data["status"] == "completed"
            assert data["sections_count"] == 1
            assert data["sources_count"] == 5
            assert data["analysis_mode"] == "fast"
            assert data["duration_seconds"] == 4.2
            assert data["report_markdown"] == "# Test Report"
            assert data["used_llm"] is False

    def test_analyze_with_llm_override(self):
        """POST /api/tender-research/analyze with LLM enabled."""
        mock_result = TenderAnalysisResult(
            status="completed",
            registry_number="123",
            sections=[],
            sections_count=0,
            sources_count=0,
            used_llm=True,
        )
        with patch(
            "src.tender_research.api.analyze_tender",
            return_value=mock_result,
        ) as mock_analyze:
            response = client.post(
                "/api/tender-research/analyze",
                json={
                    "registry_number": "123",
                    "use_llm": True,
                    "llm_base_url": "http://127.0.0.1:8088/v1",
                    "llm_model": "qwen2.5-14b",
                    "analysis_mode": "fast",
                },
            )
            assert response.status_code == 200
            assert response.json()["used_llm"] is True
            assert mock_analyze.call_args.kwargs["analysis_mode"] == "fast"

    def test_analyze_internal_error(self):
        """POST /api/tender-research/analyze returns 500 on service error."""
        with patch(
            "src.tender_research.api.analyze_tender",
            side_effect=ValueError("test error"),
        ):
            response = client.post(
                "/api/tender-research/analyze",
                json={"registry_number": "123"},
            )
            assert response.status_code == 500

    def test_analyze_warnings_and_errors(self):
        """POST /api/tender-research/analyze surfaces warnings and errors."""
        mock_result = TenderAnalysisResult(
            status="completed_with_warnings",
            registry_number="123",
            sections=[],
            sections_count=0,
            sources_count=0,
            warnings=["LLM unavailable"],
            errors=[],
        )
        with patch(
            "src.tender_research.api.analyze_tender",
            return_value=mock_result,
        ):
            response = client.post(
                "/api/tender-research/analyze",
                json={"registry_number": "123"},
            )
            data = response.json()
            assert data["status"] == "completed_with_warnings"
            assert "LLM unavailable" in data["warnings"]


class TestLatestReportEndpoint:
    def test_latest_report_not_found(self):
        """GET /api/tender-research/analyze/{registry_number}/latest returns 404 if no report."""
        response = client.get(
            "/api/tender-research/analyze/0323100010326000999/latest"
        )
        assert response.status_code == 404

    def test_latest_report_traversal_blocked(self):
        """GET /api/tender-research/analyze/.../latest blocks path traversal."""
        response = client.get(
            "/api/tender-research/analyze/../../../etc/passwd/latest"
        )
        assert response.status_code in (400, 404)

    def test_latest_report_success(self, tmp_path: Path):
        """GET /api/tender-research/analyze/{registry_number}/latest returns report."""
        registry_number = "0323100010326000013"
        reports_dir = tmp_path / "rag" / "reports"
        reports_dir.mkdir(parents=True)
        report_file = reports_dir / f"analyze_tender_{registry_number}.md"
        report_file.write_text("# Test Report Content", encoding="utf-8")

        with patch(
            "src.tender_research.api.load_config"
        ) as mock_load_config, patch(
            "src.tender_research.api.get_latest_report"
        ) as mock_get:
            mock_config = mock_load_config.return_value
            mock_config.data_dir = str(tmp_path)
            mock_record = type("MockRecord", (), {"registry_number": registry_number, "report_path": "", "created_at": None})()
            mock_get.return_value = (mock_record, "# Test Report Content", None)
            response = client.get(
                f"/api/tender-research/analyze/{registry_number}/latest"
            )
            assert response.status_code == 200
            data = response.json()
            assert data["registry_number"] == registry_number
            assert "Test Report Content" in data["report_markdown"]
