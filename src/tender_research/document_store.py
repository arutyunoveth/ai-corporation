from __future__ import annotations

import hashlib
import os
import shutil
import urllib.request
from pathlib import Path

from src.tender_research.config import TenderResearchConfig
from src.tender_research.document_text_extractor import extract_text
from src.tender_research.errors import DocumentStoreError
from src.tender_research.models import ProcurementTender
from src.tender_research.repository import TenderRepository


def download_tender_documents(
    repo: TenderRepository,
    tender: ProcurementTender,
    config: TenderResearchConfig,
) -> dict[str, int]:
    tender_dir = _tender_doc_dir(config.data_dir, tender.source, tender.external_id)
    doc_dir = tender_dir / "documents" / "original"
    text_dir = tender_dir / "documents" / "extracted_text"
    doc_dir.mkdir(parents=True, exist_ok=True)
    text_dir.mkdir(parents=True, exist_ok=True)

    documents = tender.documents
    max_bytes = config.document_download_max_size_mb * 1024 * 1024
    downloaded = 0
    failed = 0
    for doc in documents:
        if doc.download_status == "downloaded":
            downloaded += 1
            continue
        if not doc.file_url:
            doc.download_status = "skipped"
            doc.error_message = "No file_url"
            repo._session.flush()
            continue
        local_path = doc_dir / _safe_filename(doc.file_name, doc.id)
        if local_path.exists():
            doc.local_path = str(local_path)
            doc.download_status = "downloaded"
            _update_size_and_hash(doc, local_path)
            repo._session.flush()
            downloaded += 1
            _try_extract(doc, text_dir, config)
            continue
        try:
            req = urllib.request.Request(
                doc.file_url,
                headers={"User-Agent": "ArvectumTenderResearch/0.1"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                content = resp.read()
            if len(content) > max_bytes:
                doc.download_status = "skipped"
                doc.error_message = f"File too large: {len(content)} bytes"
                repo._session.flush()
                failed += 1
                continue
            local_path.write_bytes(content)
            doc.local_path = str(local_path)
            doc.download_status = "downloaded"
            _update_size_and_hash(doc, local_path)
            repo._session.flush()
            downloaded += 1
            _try_extract(doc, text_dir, config)
        except Exception as e:
            doc.download_status = "failed"
            doc.error_message = str(e)
            repo._session.flush()
            failed += 1
    return {"downloaded": downloaded, "failed": failed}


def _try_extract(doc, text_dir: Path, config: TenderResearchConfig) -> None:
    if doc.text_extraction_status in ("extracted", "unsupported", "empty"):
        return
    if not doc.local_path or not Path(doc.local_path).exists():
        return
    status, text = extract_text(doc.local_path, max_chars=config.document_extract_max_chars)
    doc.text_extraction_status = status
    if status == "extracted" and text:
        text_path = text_dir / f"{_safe_filename(doc.file_name, doc.id)}.txt"
        text_path.write_text(text, encoding="utf-8")
        doc.extracted_text_path = str(text_path)
        doc.extracted_text_chars = len(text)
    elif status == "extracted":
        doc.extracted_text_chars = 0


def _update_size_and_hash(doc, path: Path) -> None:
    doc.size_bytes = path.stat().st_size
    doc.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()


def _tender_doc_dir(base_data_dir: str, source: str, external_id: str) -> Path:
    return Path(base_data_dir) / "tenders" / source / _safe_dirname(external_id)


def _safe_filename(name: str, fallback_id: str) -> str:
    name = name.replace(" ", "_")
    name = "".join(c for c in name if c.isalnum() or c in "._-")
    if not name:
        return fallback_id
    return name[:200]


def _safe_dirname(name: str) -> str:
    safe = "".join(c for c in name if c.isalnum() or c in "_-")
    return safe[:100] or "unknown"
