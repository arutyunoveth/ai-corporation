from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape as html_escape
from pathlib import Path
import re
from typing import Literal
from xml.sax.saxutils import escape as xml_escape

from docx import Document
from docx.shared import Pt
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer

from src.modules.tender_operator_agent_demo.upload_service import (
    _load_metadata,
    get_uploaded_demo_report,
)
from src.tender_research.rag.export_service import (
    DOCX_CONTENT_TYPE,
    PDF_CONTENT_TYPE,
    _parse_markdown_blocks,
    _iter_inline_parts,
    _docx_add_formatted_paragraph,
    _ensure_pdf_font_registered,
    _pdf_styles,
    _pdf_inline_markup,
    _safe_segment,
    _short_run_id,
    _safe_output_path,
)


@dataclass(frozen=True)
class ExportedDemoReport:
    run_id: str
    registry_number: str
    format: Literal["docx", "pdf"]
    file_name: str
    file_path: str
    content_type: str
    size_bytes: int
    created_at: str
    source_report_path: str | None


_DEMO_EXPORT_SUBDIR = ("demo", "exports")


def _analysis_title(registry_number: str) -> str:
    if registry_number:
        return f"Анализ закупки {registry_number}"
    return "Отчёт demo-agent"


def _demo_metadata_lines(metadata: dict) -> list[str]:
    procurement = metadata.get("procurement") or {}
    lines = [
        f"Реестровый номер: {metadata.get('procurement_id') or ''}",
        f"Закупка: {metadata.get('tender_title') or ''}",
        f"Заказчик: {metadata.get('customer_name') or ''}",
        f"Категория: {metadata.get('tender_category') or ''}",
        f"Статус: {metadata.get('status') or ''}",
        f"Режим анализа: {metadata.get('analysis_mode') or ''}",
        f"НМЦК: {_format_nmck(procurement.get('initial_price'), procurement.get('currency'))}",
        f"Дата публикации: {metadata.get('publication_date') or ''}",
        f"Срок подачи: {metadata.get('deadline') or ''}",
        f"Источник сведений: {procurement.get('structured_source_label') or metadata.get('notice_source_label') or 'карточка ЕИС'}",
    ]
    source = metadata.get("procurement_source") or ""
    if source:
        lines.append(f"Источник: {source}")
    created = metadata.get("created_at") or ""
    if created:
        if isinstance(created, datetime):
            created = created.isoformat()
        lines.append(f"Создано: {created}")
    return lines + [""]


def _format_nmck(price, currency) -> str:
    if price is None:
        return "не указана"
    try:
        val = float(price)
        formatted = f"{val:,.2f}".replace(",", " ")
    except (ValueError, TypeError):
        formatted = str(price)
    cur = currency or "RUB"
    return f"{formatted} {cur}"


def _build_export_file_name(registry_number: str, run_id: str, format_name: Literal["docx", "pdf"]) -> str:
    safe_registry = _safe_segment(registry_number, "unknown_registry")
    return f"tender_analysis_{safe_registry}_{_short_run_id(run_id)}.{format_name}"


def _safe_output_dir(data_dir: str | None = None) -> Path:
    if data_dir:
        root = Path(data_dir).joinpath(*_DEMO_EXPORT_SUBDIR).resolve()
    else:
        root = Path.cwd().joinpath("data", *_DEMO_EXPORT_SUBDIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _build_docx_from_parts(
    title: str,
    metadata_lines: list[str],
    markdown: str,
    output_path: Path,
) -> None:
    document = Document()
    document.core_properties.title = title
    normal_style = document.styles["Normal"]
    normal_style.font.name = "Arial"
    normal_style.font.size = Pt(10.5)

    title_para = document.add_paragraph()
    title_para.style = document.styles["Title"]
    title_run = title_para.add_run(title)
    title_run.font.name = "Arial"

    for meta_line in metadata_lines:
        if meta_line:
            _docx_add_formatted_paragraph(document, meta_line)
        else:
            document.add_paragraph()

    document.add_heading("Отчёт", level=1)

    for block in _parse_markdown_blocks(markdown):
        if block.kind == "heading":
            document.add_heading(block.text, level=block.level)
        elif block.kind == "paragraph":
            _docx_add_formatted_paragraph(document, block.text)
        elif block.kind == "bullet_list":
            for item in block.items:
                _docx_add_formatted_paragraph(document, item, style="List Bullet")
        elif block.kind == "numbered_list":
            for item in block.items:
                _docx_add_formatted_paragraph(document, item, style="List Number")

    document.save(output_path)


def _build_pdf_from_parts(
    title: str,
    metadata_lines: list[str],
    markdown: str,
    output_path: Path,
) -> None:
    font_name = _ensure_pdf_font_registered()
    styles = _pdf_styles(font_name)
    story = [
        Paragraph(html_escape(title), styles["title"]),
        Spacer(1, 2 * mm),
    ]

    for meta_line in metadata_lines:
        if meta_line:
            story.append(Paragraph(_pdf_inline_markup(meta_line), styles["meta"]))
        else:
            story.append(Spacer(1, 2 * mm))

    story.append(Paragraph("Отчёт", styles["h1"]))

    for block in _parse_markdown_blocks(markdown):
        if block.kind == "heading":
            story.append(Paragraph(_pdf_inline_markup(block.text), styles[f"h{block.level}"]))
        elif block.kind == "paragraph":
            story.append(Paragraph(_pdf_inline_markup(block.text), styles["body"]))
        elif block.kind == "bullet_list":
            items = [ListItem(Paragraph(_pdf_inline_markup(item), styles["body"])) for item in block.items]
            story.append(ListFlowable(items, bulletType="bullet", start="circle"))
        elif block.kind == "numbered_list":
            items = [ListItem(Paragraph(_pdf_inline_markup(item), styles["body"])) for item in block.items]
            story.append(ListFlowable(items, bulletType="1"))

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title=title,
    )
    doc.build(story)


def export_demo_agent_report_docx(run_id: str) -> ExportedDemoReport:
    metadata = _load_metadata(run_id)
    report = get_uploaded_demo_report(run_id)
    report_markdown = report.report_markdown

    registry_number = metadata.get("procurement_id") or metadata.get("reestr_number") or ""
    title = _analysis_title(registry_number)
    metadata_lines = _demo_metadata_lines(metadata)

    root = _safe_output_dir()
    file_name = _build_export_file_name(registry_number, run_id, "docx")
    output_path = _safe_output_path(root, file_name)

    _build_docx_from_parts(title, metadata_lines, report_markdown, output_path)

    return ExportedDemoReport(
        run_id=run_id,
        registry_number=registry_number,
        format="docx",
        file_name=file_name,
        file_path=str(output_path),
        content_type=DOCX_CONTENT_TYPE,
        size_bytes=output_path.stat().st_size,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_report_path=str(metadata.get("_metadata_path", "")),
    )


def export_demo_agent_report_pdf(run_id: str) -> ExportedDemoReport:
    metadata = _load_metadata(run_id)
    report = get_uploaded_demo_report(run_id)
    report_markdown = report.report_markdown

    registry_number = metadata.get("procurement_id") or metadata.get("reestr_number") or ""
    title = _analysis_title(registry_number)
    metadata_lines = _demo_metadata_lines(metadata)

    root = _safe_output_dir()
    file_name = _build_export_file_name(registry_number, run_id, "pdf")
    output_path = _safe_output_path(root, file_name)

    _build_pdf_from_parts(title, metadata_lines, report_markdown, output_path)

    return ExportedDemoReport(
        run_id=run_id,
        registry_number=registry_number,
        format="pdf",
        file_name=file_name,
        file_path=str(output_path),
        content_type=PDF_CONTENT_TYPE,
        size_bytes=output_path.stat().st_size,
        created_at=datetime.now(timezone.utc).isoformat(),
        source_report_path=str(metadata.get("_metadata_path", "")),
    )
