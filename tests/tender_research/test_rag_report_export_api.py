from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from src.main import app
from src.tender_research.rag.export_service import DOCX_CONTENT_TYPE, PDF_CONTENT_TYPE, ExportedReport

client = TestClient(app)


def _exported_report(tmp_path: Path, *, format_name: str) -> ExportedReport:
    file_name = f"tender_analysis_0323100010326000013_run001.{format_name}"
    path = tmp_path / file_name
    path.write_bytes(b"%PDF-1.4\nstub" if format_name == "pdf" else b"PK\x03\x04docx")
    return ExportedReport(
        analysis_run_id="run-001",
        registry_number="0323100010326000013",
        format=format_name,  # type: ignore[arg-type]
        file_name=file_name,
        file_path=str(path),
        content_type=DOCX_CONTENT_TYPE if format_name == "docx" else PDF_CONTENT_TYPE,
        size_bytes=path.stat().st_size,
        created_at="2026-07-06T09:00:00+00:00",
        source_report_path="data/rag/reports/report.md",
    )


def test_get_export_docx_returns_file(tmp_path: Path) -> None:
    with patch("src.tender_research.api.export_analysis_report_docx", return_value=_exported_report(tmp_path, format_name="docx")), patch(
        "src.tender_research.api.analyze_tender"
    ) as mock_analyze:
        response = client.get("/api/tender-research/analyze/history/run-001/export/docx")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(DOCX_CONTENT_TYPE)
    assert ".docx" in response.headers["content-disposition"]
    assert response.content
    mock_analyze.assert_not_called()


def test_get_export_pdf_returns_file(tmp_path: Path) -> None:
    with patch("src.tender_research.api.export_analysis_report_pdf", return_value=_exported_report(tmp_path, format_name="pdf")), patch(
        "src.tender_research.api.analyze_tender"
    ) as mock_analyze:
        response = client.get("/api/tender-research/analyze/history/run-001/export/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith(PDF_CONTENT_TYPE)
    assert ".pdf" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")
    mock_analyze.assert_not_called()


def test_unknown_run_id_returns_404() -> None:
    with patch("src.tender_research.api.export_analysis_report_docx", side_effect=FileNotFoundError("Analysis run not found")):
        response = client.get("/api/tender-research/analyze/history/run-missing/export/docx")

    assert response.status_code == 404
    assert response.json()["detail"] == "Analysis run not found"


def test_missing_report_returns_clear_error() -> None:
    with patch(
        "src.tender_research.api.export_analysis_report_pdf",
        side_effect=FileNotFoundError("Report file is missing or inaccessible"),
    ):
        response = client.get("/api/tender-research/analyze/history/run-missing-report/export/pdf")

    assert response.status_code == 404
    assert response.json()["detail"] == "Report file is missing or inaccessible"
