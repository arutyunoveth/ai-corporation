from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any

from src.modules.tender_operator_agent_demo.attachment_downloader import (
    AttachmentDownloadResult,
    download_procurement_attachments,
)
from src.modules.tender_operator_agent_demo.procurement_schemas import ProcurementAttachment
from src.modules.tender_operator_agent_demo.schemas import ResellerTenderSearchResult
from src.modules.tender_operator_agent_demo.upload_service import _extract_goods_spec_table
from src.modules.tender_connectors.text_extraction import extract_text_from_attachment_bytes
from src.tender_research.providers.public_44fz_search import (
    Public44FzSearchProvider,
    PublicTenderDetail,
)


def fetch_live_card_details(
    search_result: ResellerTenderSearchResult,
) -> tuple[dict[str, Any] | None, str]:
    provider = Public44FzSearchProvider(timeout_seconds=15)
    try:
        detail: PublicTenderDetail = provider.fetch_detail(
            registry_number=search_result.procurement_id,
            card_url=search_result.source_url,
        )
    except Exception:
        return None, "unavailable"

    if detail.network_status != "success":
        return None, "unavailable"

    enriched: dict[str, Any] = {}

    if detail.title:
        enriched["title"] = detail.title
    if detail.customer_name:
        enriched["customer_name"] = detail.customer_name
    if detail.customer_inn:
        enriched["customer_inn"] = detail.customer_inn
    if detail.nmck_amount is not None:
        enriched["initial_price"] = float(detail.nmck_amount)
    if detail.publication_date:
        enriched["publication_date"] = detail.publication_date.isoformat()
    if detail.application_deadline:
        enriched["deadline"] = detail.application_deadline.isoformat()

    enriched["card_url"] = detail.card_url
    enriched["registry_number"] = detail.registry_number
    enriched["detail_raw_source"] = "eis_html"
    enriched["common_info_html"] = detail.common_info_html

    has_docs = bool(detail.document_links)
    enriched["live_document_links"] = [
        {
            "title": d.title or d.file_name,
            "url": d.url,
            "file_name": d.file_name,
            "content_type": d.content_type,
            "size_bytes": d.size_bytes,
        }
        for d in (detail.document_links or [])
    ]
    enriched["live_document_count"] = len(detail.document_links or [])
    enriched["attachments_status"] = "live_available" if has_docs else "live_no_documents"
    enriched["attachments_count"] = len(detail.document_links or [])

    if detail.card_url:
        enriched["source_url"] = detail.card_url

    status = "loaded" if has_docs else "partial"
    return enriched, status


def download_live_documents(
    document_links: list[dict[str, Any]],
    *,
    target_dir: str | None = None,
) -> dict[str, Any]:
    if not document_links:
        return {
            "status": "not_found",
            "total_count": 0,
            "downloaded_count": 0,
            "files": [],
        }

    attachments: list[ProcurementAttachment] = []
    for i, link in enumerate(document_links, start=1):
        url = link.get("url", "")
        if not url:
            continue
        name = link.get("file_name") or link.get("title") or f"attachment_{i}"
        ext = Path(name).suffix.lower() or ".bin"
        attachments.append(ProcurementAttachment(
            attachment_id=f"live-{i:03d}",
            name=name,
            url=url,
            content_type=link.get("content_type"),
            size_bytes=link.get("size_bytes"),
            extension=ext,
            can_download=True,
            requires_manual_upload=False,
        ))

    if target_dir:
        dl_dir = Path(target_dir)
        dl_dir.mkdir(parents=True, exist_ok=True)
    else:
        dl_dir = Path(tempfile.mkdtemp(prefix="live-docs-"))

    try:
        result: AttachmentDownloadResult = download_procurement_attachments(
            attachments,
            target_dir=dl_dir,
            max_attachments=30,
            max_file_size_bytes=50 * 1024 * 1024,
            max_total_size_bytes=200 * 1024 * 1024,
        )
    except Exception:
        return {
            "status": "failed",
            "total_count": len(document_links),
            "downloaded_count": 0,
            "files": [],
            "error": "Ошибка при скачивании документов",
        }

    file_list: list[dict[str, Any]] = []
    for saved in result.saved:
        file_path = str(dl_dir / (saved.stored_name or saved.name))
        file_list.append({
            "name": saved.name,
            "stored_name": saved.stored_name or saved.name,
            "path": file_path,
            "size_bytes": saved.size_bytes,
            "extension": saved.extension,
        })

    if result.saved:
        status = "downloaded"
    elif result.skipped:
        status = "partially_downloaded"
    else:
        status = "failed"

    return {
        "status": status,
        "total_count": len(document_links),
        "downloaded_count": len(result.saved),
        "skipped_count": len(result.skipped),
        "files": file_list,
    }


def extract_document_texts(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    texts: list[dict[str, Any]] = []
    for f in files:
        path = f.get("path", "")
        name = f.get("name", "document")
        try:
            content = Path(path).read_bytes()
        except Exception:
            continue
        try:
            text = extract_text_from_attachment_bytes(url=path, content=content)
        except Exception:
            text = None
        if text and len(text.strip()) > 20:
            texts.append({"name": name, "text": text, "path": path})
    return texts


def parse_line_items_from_texts(texts: list[dict[str, Any]]) -> list[dict[str, str]]:
    all_rows: list[dict[str, str]] = []
    seen: set[str] = set()
    for item in texts:
        if not item.get("text"):
            continue
        try:
            rows = _extract_goods_spec_table(item["text"])
        except Exception:
            rows = []
        for row in rows:
            key = row.get("Наименование", "").strip().lower()
            if key and key not in seen:
                seen.add(key)
                all_rows.append(row)
    return all_rows


def build_line_items_from_spec_rows(
    rows: list[dict[str, str]],
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for row in rows:
        name = row.get("Наименование", "Позиция")
        unit = row.get("Ед. изм.", "")
        quantity_raw = row.get("Кол-во", "")
        try:
            quantity = float(quantity_raw.replace(",", ".")) if quantity_raw and quantity_raw != "не указано" else None
        except (ValueError, AttributeError):
            quantity = None
        characteristics = row.get("Характеристики", "")
        items.append({
            "item_name": name,
            "quantity": quantity,
            "unit": unit if unit != "—" else None,
            "characteristics": characteristics if characteristics and characteristics != "Требуется сверка характеристик по ТЗ." else None,
            "evidence": f"Из технического задания: {name}",
        })
    return items
