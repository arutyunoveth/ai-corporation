from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from docx import Document

from src.tender_research.rag.export_service import (
    export_analysis_report_docx,
    export_analysis_report_pdf,
    get_exported_report_path,
)


class _MockHistoryRecord:
    def __init__(
        self,
        *,
        run_id: str = "run-001",
        registry_number: str = "0323100010326000013",
        report_path: str | None = "data/rag/reports/analyze_tender_0323100010326000013.md",
    ) -> None:
        self.id = run_id
        self.registry_number = registry_number
        self.status = "completed"
        self.used_llm = True
        self.llm_model = "/Users/master/models/Qwen2.5-14B-Instruct-Q4_K_M.gguf"
        self.retrieval_provider = "llama_cpp"
        self.retrieval_model = "Qwen3-Embedding-4B"
        self.sections_count = 10
        self.sources_count = 34
        self.report_path = report_path
        self.report_markdown_preview = "# Анализ закупки"
        self.warnings = []
        self.errors = []
        self.duration_seconds = 146.26
        self.source = "api"
        self.metadata = {"analysis_mode": "fast"}
        self.created_at = datetime(2026, 7, 6, 6, 9, 1, tzinfo=timezone.utc)
        self.updated_at = self.created_at


def test_export_docx_by_analysis_run_id(tmp_path: Path) -> None:
    record = _MockHistoryRecord(run_id="31a34446-9122-4c52-92ee-8988fa1e3546")
    markdown = "# Анализ закупки\n\n## Сводка\n\nОсновной текст отчёта.\n\n- Первый пункт\n- Второй пункт"

    with patch(
        "src.tender_research.rag.export_service.get_analysis_run_report",
        return_value=(record, markdown, None),
    ):
        exported = export_analysis_report_docx(
            record.id,
            output_dir=tmp_path,
            data_dir=str(tmp_path),
            session=object(),
        )

    assert exported.analysis_run_id == record.id
    assert exported.registry_number == record.registry_number
    assert exported.format == "docx"
    assert exported.file_name.endswith(".docx")
    assert exported.content_type.endswith("document")
    assert exported.size_bytes > 0

    output_path = Path(exported.file_path)
    assert output_path.exists()
    assert output_path.parent == tmp_path.resolve()
    assert output_path.name == "tender_analysis_0323100010326000013_31a34446.docx"

    document = Document(output_path)
    full_text = "\n".join(paragraph.text for paragraph in document.paragraphs)
    assert "0323100010326000013" in full_text
    assert "Основной текст отчёта." in full_text
    assert "Первый пункт" in full_text


def test_export_pdf_by_analysis_run_id(tmp_path: Path) -> None:
    record = _MockHistoryRecord(run_id="654fc9b0-2d64-494e-a764-49e7e1e1cc38")
    markdown = "# Анализ закупки\n\nКириллица проверяется здесь.\n\n## Раздел\n\nОсновной текст отчёта."

    with patch(
        "src.tender_research.rag.export_service.get_analysis_run_report",
        return_value=(record, markdown, None),
    ):
        exported = export_analysis_report_pdf(
            record.id,
            output_dir=tmp_path,
            data_dir=str(tmp_path),
            session=object(),
        )

    output_path = Path(exported.file_path)
    payload = output_path.read_bytes()
    assert exported.format == "pdf"
    assert exported.file_name.endswith(".pdf")
    assert exported.content_type == "application/pdf"
    assert exported.size_bytes > 0
    assert output_path.parent == tmp_path.resolve()
    assert payload.startswith(b"%PDF")


def test_unknown_analysis_run_id_raises_not_found(tmp_path: Path) -> None:
    with patch(
        "src.tender_research.rag.export_service.get_analysis_run_report",
        return_value=(None, None, "Run not found"),
    ):
        try:
            export_analysis_report_docx("missing-run", output_dir=tmp_path, data_dir=str(tmp_path), session=object())
        except FileNotFoundError as exc:
            assert "Run not found" in str(exc)
        else:
            raise AssertionError("Expected FileNotFoundError")


def test_missing_report_path_raises_not_found(tmp_path: Path) -> None:
    record = _MockHistoryRecord(report_path=None)
    with patch(
        "src.tender_research.rag.export_service.get_analysis_run_report",
        return_value=(record, None, "No report file was saved for this run"),
    ):
        try:
            export_analysis_report_pdf(record.id, output_dir=tmp_path, data_dir=str(tmp_path), session=object())
        except FileNotFoundError as exc:
            assert "No report file was saved for this run" in str(exc)
        else:
            raise AssertionError("Expected FileNotFoundError")


def test_safe_file_name_and_output_path_stay_inside_export_dir(tmp_path: Path) -> None:
    record = _MockHistoryRecord(run_id="../bad-run", registry_number="../../etc/passwd")
    markdown = "# Анализ закупки\n\nБезопасный путь."

    with patch(
        "src.tender_research.rag.export_service.get_analysis_run_report",
        return_value=(record, markdown, None),
    ):
        exported = export_analysis_report_docx(
            record.id,
            output_dir=tmp_path,
            data_dir=str(tmp_path),
            session=object(),
        )

    output_path = Path(exported.file_path)
    assert output_path.exists()
    assert output_path.resolve().is_relative_to(tmp_path.resolve())
    assert ".." not in output_path.name


def test_get_exported_report_path_returns_existing_file(tmp_path: Path) -> None:
    record = _MockHistoryRecord(run_id="run-keep")
    expected = tmp_path / "tender_analysis_0323100010326000013_run-keep.docx"
    expected.write_bytes(b"stub")

    with patch("src.tender_research.rag.export_service.get_analysis_run", return_value=record):
        path = get_exported_report_path(
            record.id,
            "docx",
            output_dir=tmp_path,
            data_dir=str(tmp_path),
            session=object(),
        )

    assert path == expected.resolve()
