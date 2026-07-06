from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.modules.tender_operator_agent_demo.report_export_service import (
    ExportedDemoReport,
    export_demo_agent_report_docx,
    export_demo_agent_report_pdf,
)
from src.modules.tender_operator_agent_demo.schemas import TenderOperatorDemoReportResponse


SAMPLE_METADATA = {
    "run_id": "toa-run-test-00000000-abc123",
    "created_at": "2026-07-06T12:00:00+00:00",
    "mode": "procurement_search_intake",
    "tender_title": "Тестовая закупка",
    "tender_category": "44-ФЗ",
    "customer_name": "ООО Тестовый Заказчик",
    "status": "needs_review",
    "analysis_mode": "fallback_deterministic_adapter",
    "procurement_source": "zakupki_gov_ru_getdocs_ip",
    "procurement_id": "0123456789012345",
    "procurement_url": "https://zakupki.gov.ru/example",
    "publication_date": "06.07.2026",
    "deadline": "20.07.2026",
    "notice_source_label": "электронное извещение ЕИС",
    "procurement": {
        "initial_price": 1234567.89,
        "currency": "RUB",
        "structured_source_label": "электронное извещение ЕИС",
    },
}

SAMPLE_REPORT_MARKDOWN = """# Отчёт по загруженному прогону тендерного агента

- Run ID: toa-run-test-00000000-abc123
- Закупка: Тестовая закупка
- Категория: 44-ФЗ
- Заказчик: ООО Тестовый Заказчик
- Статус: needs_review
- Режим анализа: fallback_deterministic_adapter

## Источник закупки
- Источник: zakupki_gov_ru_getdocs_ip
- Номер извещения: 0123456789012345
- Заказчик: ООО Тестовый Заказчик
- Закон: 44-ФЗ
- НМЦК: 1234567.89 RUB
- Срок подачи: 20.07.2026
- Источник сведений: электронное извещение ЕИС
- Статус скачивания: downloaded
- Ручная загрузка требовалась: нет
- Скачано/добавлено файлов: 1

### Документация
- documentation-archive.zip

## Краткий вывод
- Тестовый вывод.
- Анализ выполнен.

## Предварительный анализ закупки
### Ключевые требования и ограничения
- Требуется ручная валидация.

## Экономика
- Минимальная закупочная стоимость: 1000000.00
- Целевая маржа: 15%

## Ручные проверки
- Тестовая проверка 1.
- Тестовая проверка 2.
"""


@pytest.fixture(autouse=True)
def _clean_exports(tmp_path):
    with patch("src.modules.tender_operator_agent_demo.report_export_service._safe_output_dir", return_value=tmp_path):
        yield


@pytest.fixture
def mock_run_data():
    with (
        patch("src.modules.tender_operator_agent_demo.report_export_service._load_metadata", return_value=SAMPLE_METADATA),
        patch(
            "src.modules.tender_operator_agent_demo.report_export_service.get_uploaded_demo_report",
            return_value=TenderOperatorDemoReportResponse(
                run_id="toa-run-test-00000000-abc123",
                report_title="Отчёт по загруженному прогону тендерного агента",
                generated_at="2026-07-06T12:00:00",
                recommendation="manual_review_required",
                recommendation_label="нужна ручная проверка",
                executive_summary=["Тестовый вывод.", "Анализ выполнен."],
                manual_checks=["Тестовая проверка 1.", "Тестовая проверка 2."],
                sections=[],
                report_markdown=SAMPLE_REPORT_MARKDOWN,
            ),
        ),
    ):
        yield


class TestDocxExport:
    def test_export_docx_creates_file(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_docx("toa-run-test-00000000-abc123")
        assert result.format == "docx"
        assert result.file_name.endswith(".docx")
        path = Path(result.file_path)
        assert path.exists()
        assert path.suffix == ".docx"
        assert path.stat().st_size > 0

    def test_export_docx_content_type(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_docx("toa-run-test-00000000-abc123")
        assert "wordprocessingml.document" in result.content_type

    def test_export_docx_filename_pattern(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_docx("toa-run-test-00000000-abc123")
        assert result.file_name.startswith("tender_analysis_")
        assert "0123456789012345" in result.file_name

    def test_export_docx_contains_key_fields(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_docx("toa-run-test-00000000-abc123")
        from docx import Document
        doc = Document(result.file_path)
        text = " ".join(p.text for p in doc.paragraphs)
        assert "0123456789012345" in text
        assert "электронное извещение ЕИС" in text
        assert "1234567.89" in text or "1 234 567" in text
        assert "06.07.2026" in text
        assert "20.07.2026" in text

    def test_export_docx_registry_number_and_run_id(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_docx("toa-run-test-00000000-abc123")
        assert result.registry_number == "0123456789012345"
        assert result.run_id == "toa-run-test-00000000-abc123"


class TestPdfExport:
    def test_export_pdf_creates_file(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_pdf("toa-run-test-00000000-abc123")
        assert result.format == "pdf"
        assert result.file_name.endswith(".pdf")
        path = Path(result.file_path)
        assert path.exists()
        assert path.suffix == ".pdf"
        assert path.stat().st_size > 0

    def test_export_pdf_content_type(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_pdf("toa-run-test-00000000-abc123")
        assert result.content_type == "application/pdf"

    def test_export_pdf_magic_bytes(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_pdf("toa-run-test-00000000-abc123")
        with open(result.file_path, "rb") as f:
            header = f.read(5)
        assert header == b"%PDF-"

    def test_export_pdf_filename_pattern(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_pdf("toa-run-test-00000000-abc123")
        assert result.file_name.startswith("tender_analysis_")
        assert "0123456789012345" in result.file_name

    def test_export_pdf_has_valid_size_and_metadata(self, mock_run_data, tmp_path):
        result = export_demo_agent_report_pdf("toa-run-test-00000000-abc123")
        assert result.file_name.startswith("tender_analysis_")
        assert "0123456789012345" in result.file_name
        assert result.file_name.endswith(".pdf")
        assert Path(result.file_path).stat().st_size > 1000


class TestErrors:
    def test_unknown_run_id_raises_not_found(self):
        from fastapi import HTTPException
        from src.modules.tender_operator_agent_demo.upload_service import _load_metadata as real_load
        real_load_ref = real_load
        with patch("src.modules.tender_operator_agent_demo.report_export_service._load_metadata") as mock_load:
            mock_load.side_effect = HTTPException(status_code=404, detail="Run not found")
            with pytest.raises(HTTPException, match="Run not found"):
                export_demo_agent_report_docx("nonexistent-run")

    def test_report_not_available(self):
        from fastapi import HTTPException
        with (
            patch("src.modules.tender_operator_agent_demo.report_export_service._load_metadata", return_value=SAMPLE_METADATA),
            patch("src.modules.tender_operator_agent_demo.report_export_service.get_uploaded_demo_report") as mock_report,
        ):
            mock_report.side_effect = HTTPException(status_code=404, detail="Report is not available yet")
            with pytest.raises(HTTPException, match="Report is not available yet"):
                export_demo_agent_report_docx("toa-run-test-00000000-abc123")
