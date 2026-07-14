from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from html import escape as html_escape, unescape as html_unescape
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
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.modules.tender_operator_agent_demo.upload_service import (
    _load_metadata,
    get_uploaded_demo_report,
    get_uploaded_demo_report_html,
    get_demo_run_output_dir,
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
_SAFE_RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{2,127}$")


def _analysis_title(registry_number: str) -> str:
    if registry_number:
        return f"Анализ закупки {registry_number}"
    return "Отчёт demo-agent"


def _validate_run_id(run_id: str) -> str:
    normalized = str(run_id or "").strip()
    if not normalized:
        raise ValueError("Run ID must not be empty")
    if "/" in normalized or "\\" in normalized or ".." in normalized:
        raise ValueError("Invalid run ID")
    if not _SAFE_RUN_ID_RE.fullmatch(normalized):
        raise ValueError("Invalid run ID")
    return normalized


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
    return f"demo_agent_report_{safe_registry}_{_short_run_id(run_id)}.{format_name}"


def _safe_output_dir(data_dir: str | None = None) -> Path:
    if data_dir:
        root = Path(data_dir).joinpath(*_DEMO_EXPORT_SUBDIR).resolve()
    else:
        root = Path.cwd().joinpath("data", *_DEMO_EXPORT_SUBDIR).resolve()
    root.mkdir(parents=True, exist_ok=True)
    return root


def _html_report_to_markdown(html: str) -> str:
    cleaned = re.sub(r"(?is)<(script|style)\b.*?>.*?</\1>", " ", html or "")
    replacements = [
        (r"(?i)<br\s*/?>", "\n"),
        (r"(?i)</p\s*>", "\n\n"),
        (r"(?i)</div\s*>", "\n"),
        (r"(?i)</li\s*>", "\n"),
        (r"(?i)<li\b[^>]*>", "- "),
        (r"(?i)</h1\s*>", "\n\n"),
        (r"(?i)</h2\s*>", "\n\n"),
        (r"(?i)</h3\s*>", "\n\n"),
        (r"(?i)<h1\b[^>]*>", "# "),
        (r"(?i)<h2\b[^>]*>", "## "),
        (r"(?i)<h3\b[^>]*>", "### "),
        (r"(?i)</tr\s*>", "\n"),
        (r"(?i)</td\s*>", " | "),
        (r"(?i)</th\s*>", " | "),
    ]
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned)
    cleaned = re.sub(r"(?is)<[^>]+>", " ", cleaned)
    cleaned = html_unescape(cleaned)
    cleaned = re.sub(r"[ \t]+\n", "\n", cleaned)
    cleaned = re.sub(r"\n[ \t]+", "\n", cleaned)
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _report_markdown_for_export(run_id: str, report_markdown: str | None) -> str:
    if (report_markdown or "").strip():
        return str(report_markdown).strip()
    return _html_report_to_markdown(get_uploaded_demo_report_html(run_id))


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


def _load_canonical_report(run_id: str) -> dict | None:
    path = get_demo_run_output_dir(run_id) / "canonical_report.json"
    if not path.is_file():
        return None
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def _build_docx_from_canonical(model: dict, title: str, output_path: Path) -> None:
    document = Document(); document.add_heading(title, 0)
    summary, passport = model["executive_summary"], model["procurement_passport"]
    for line in (f"Предмет: {summary['subject']}", f"НМЦК (максимальная цена закупки): {summary['nmck']} {summary['currency']}", f"Решение: {summary['decision']}", f"ОКПД2: {passport.get('okpd2')}"):
        document.add_paragraph(line)
    document.add_heading("Перечень услуг и единичных расценок", 1)
    table = document.add_table(rows=1, cols=6); table.style = "Table Grid"
    for cell, label in zip(table.rows[0].cells, ("№", "Услуга", "Единица", "Единичная цена", "Объём", "Источник")): cell.text = label
    for row in model["service_catalog"]:
        cells = table.add_row().cells
        values = (row["sequence"], row["original_name"], row["unit_original"], f"{row['unit_price']} RUB", row["quantity_display"], f"{row['source_document_id']}, {row['source_row']} [{', '.join(row['evidence_ids'])}]")
        for cell, value in zip(cells, values): cell.text = str(value)
    document.add_heading("Ограничения анализа", 1)
    for item in model["missing_data"]: document.add_paragraph(item["description"], style="List Bullet")
    for item in model["limitations"]: document.add_paragraph(item, style="List Bullet")
    document.add_heading("Evidence map", 1)
    for item in model["evidence_map"]: document.add_paragraph(f"[{item['evidence_id']}] {item['document']}, строка {item['row']}: {item['short_excerpt']}", style="List Bullet")
    document.save(output_path)


def _build_pdf_from_canonical(model: dict, title: str, output_path: Path) -> None:
    font_name = _ensure_pdf_font_registered(); styles = _pdf_styles(font_name)
    summary, passport = model["executive_summary"], model["procurement_passport"]
    story = [Paragraph(html_escape(title), styles["title"]), Paragraph(_pdf_inline_markup(f"Предмет: {summary['subject']}"), styles["body"]), Paragraph(_pdf_inline_markup(f"НМЦК (максимальная цена закупки): {summary['nmck']} {summary['currency']}; ОКПД2: {passport.get('okpd2')}"), styles["body"]), Paragraph(_pdf_inline_markup(f"Решение: {summary['decision']}"), styles["body"]), Paragraph("Перечень услуг и единичных расценок", styles["h1"])]
    data = [[Paragraph(value, styles["body"]) for value in ("№", "Услуга", "Ед.", "Цена", "Объём", "Источник")]]
    for row in model["service_catalog"]:
        data.append([Paragraph(_pdf_inline_markup(str(value)), styles["body"]) for value in (row["sequence"], row["original_name"], row["unit_original"], f"{row['unit_price']} RUB", row["quantity_display"], f"[{', '.join(row['evidence_ids'])}]")])
    table = Table(data, colWidths=[8*mm, 58*mm, 25*mm, 22*mm, 30*mm, 27*mm], repeatRows=1)
    table.setStyle(TableStyle([("GRID", (0,0), (-1,-1), .25, HexColor("#b9c8d0")), ("BACKGROUND", (0,0), (-1,0), HexColor("#e9f7f5")), ("VALIGN", (0,0), (-1,-1), "TOP")]))
    story += [table, Paragraph("Ограничения анализа", styles["h1"])]
    story += [Paragraph(_pdf_inline_markup(item["description"]), styles["body"]) for item in model["missing_data"]]
    story += [Paragraph(_pdf_inline_markup(item), styles["body"]) for item in model["limitations"]]
    story.append(Paragraph("Evidence map", styles["h1"]))
    story += [Paragraph(_pdf_inline_markup(f"[{item['evidence_id']}] {item['document']}, строка {item['row']}: {item['short_excerpt']}"), styles["body"]) for item in model["evidence_map"]]
    doc = SimpleDocTemplate(str(output_path), pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=14*mm, bottomMargin=14*mm, title=title); doc.build(story)


def export_demo_agent_report_docx(run_id: str) -> ExportedDemoReport:
    run_id = _validate_run_id(run_id)
    metadata = _load_metadata(run_id)
    report = get_uploaded_demo_report(run_id)
    report_markdown = _report_markdown_for_export(run_id, report.report_markdown)

    registry_number = metadata.get("procurement_id") or metadata.get("reestr_number") or ""
    title = _analysis_title(registry_number)
    metadata_lines = _demo_metadata_lines(metadata)

    root = _safe_output_dir()
    file_name = _build_export_file_name(registry_number, run_id, "docx")
    output_path = _safe_output_path(root, file_name)
    canonical = _load_canonical_report(run_id)
    if canonical:
        _build_docx_from_canonical(canonical, title, output_path)
    else:
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
    run_id = _validate_run_id(run_id)
    metadata = _load_metadata(run_id)
    report = get_uploaded_demo_report(run_id)
    report_markdown = _report_markdown_for_export(run_id, report.report_markdown)

    registry_number = metadata.get("procurement_id") or metadata.get("reestr_number") or ""
    title = _analysis_title(registry_number)
    metadata_lines = _demo_metadata_lines(metadata)

    root = _safe_output_dir()
    file_name = _build_export_file_name(registry_number, run_id, "pdf")
    output_path = _safe_output_path(root, file_name)
    canonical = _load_canonical_report(run_id)
    if canonical:
        _build_pdf_from_canonical(canonical, title, output_path)
    else:
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
