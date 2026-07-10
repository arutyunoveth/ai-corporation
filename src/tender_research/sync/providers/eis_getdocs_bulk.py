from __future__ import annotations

import hashlib
import io
import json
import time
import zipfile
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from xml.etree import ElementTree as ET

from sqlalchemy.orm import Session

from src.modules.tender_operator_agent_demo.settings import get_zakupki_soap_settings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import ZakupkiSoapClient
from src.shared.db.base import utcnow
from src.tender_research.dedupe import content_hash
from src.tender_research.repository import TenderRepository
from src.tender_research.sync.eis_params import format_eis_exact_date, normalize_eis_region_code


PROVIDER = "eis_getdocs_bulk"
MAX_ZIP_FILES = 1_000
MAX_ZIP_UNPACKED_BYTES = 250 * 1024 * 1024
MAX_XML_BYTES = 15 * 1024 * 1024


@dataclass
class ParsedXmlResult:
    file_name: str
    status: str
    tender: dict | None = None
    error: str | None = None


@dataclass
class BulkFetchResult:
    provider: str
    region: str
    exact_date: str
    subsystem: str
    document_type: str
    request_id: str | None
    archive_urls: list[str] = field(default_factory=list)
    archive_count: int = 0
    archives_downloaded: int = 0
    archives_deduplicated: int = 0
    archives_unchanged: int = 0
    xml_count: int = 0
    parsed_count: int = 0
    failed_count: int = 0
    elapsed_ms: int = 0
    records_inserted: int = 0
    records_updated: int = 0
    records_unchanged: int = 0
    errors: list[dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "region": self.region,
            "exact_date": self.exact_date,
            "subsystem": self.subsystem,
            "document_type": self.document_type,
            "request_id": self.request_id,
            "archive_urls": self.archive_urls,
            "archive_count": self.archive_count,
            "archives_found": self.archive_count,
            "archives_downloaded": self.archives_downloaded,
            "archives_deduplicated": self.archives_deduplicated,
            "archives_unchanged": self.archives_unchanged,
            "xml_count": self.xml_count,
            "xml_total": self.xml_count,
            "xml_parsed": self.parsed_count,
            "xml_failed": self.failed_count,
            "parsed_count": self.parsed_count,
            "failed_count": self.failed_count,
            "elapsed_ms": self.elapsed_ms,
            "records_inserted": self.records_inserted,
            "records_updated": self.records_updated,
            "records_unchanged": self.records_unchanged,
            "errors": self.errors,
        }


class EisGetDocsBulkProvider:
    def __init__(self, *, client: ZakupkiSoapClient | None = None, repository: TenderRepository | None = None):
        settings = get_zakupki_soap_settings()
        if settings.token_owner != "individual":
            raise ValueError("GetDocsIP bulk provider requires an individual token")
        self.client = client or ZakupkiSoapClient(settings)
        self.repository = repository

    def fetch_archives(
        self,
        region_code: str | int,
        exact_date: date | datetime | str,
        subsystem_type: str = "PRIZ",
        document_type: str = "epNotificationEF2020",
    ) -> BulkFetchResult:
        started = time.monotonic()
        region = normalize_eis_region_code(region_code)
        formatted_date = format_eis_exact_date(exact_date, timezone="Europe/Moscow")
        result = self.client.get_docs_by_org_region(
            region,
            formatted_date,
            document_type,
            subsystem_type=subsystem_type,
        )
        elapsed_ms = int((time.monotonic() - started) * 1000)
        return BulkFetchResult(
            provider=PROVIDER,
            region=region,
            exact_date=formatted_date,
            subsystem=subsystem_type,
            document_type=document_type,
            request_id=result.request_id,
            archive_urls=result.archive_urls or ([result.archive_url] if result.archive_url else []),
            archive_count=len(result.archive_urls or ([result.archive_url] if result.archive_url else [])),
            elapsed_ms=elapsed_ms,
            errors=[{"status": result.status, "message": "; ".join(result.warnings)}] if result.status != "completed" else [],
        )

    def fetch_procurements(
        self,
        *,
        region_code: str | int,
        exact_date: date | datetime | str,
        subsystem_type: str = "PRIZ",
        document_type: str = "epNotificationEF2020",
        max_archives: int | None = None,
        download_dir: str | Path | None = None,
    ) -> BulkFetchResult:
        result = self.fetch_archives(region_code, exact_date, subsystem_type, document_type)
        urls = result.archive_urls[:max_archives] if max_archives else result.archive_urls
        source_day = _parse_exact_date(result.exact_date)
        target_dir = Path(download_dir or "data/eis_bulk/raw_archives")
        target_dir.mkdir(parents=True, exist_ok=True)
        for archive_url in urls:
            try:
                payload = self._download_archive_bytes(archive_url, target_dir)
                result.archives_downloaded += 1
                sha256 = hashlib.sha256(payload).hexdigest()
                existing_archive = self.repository.get_source_archive_by_sha(PROVIDER, sha256) if self.repository else None
                if existing_archive is not None:
                    result.archives_deduplicated += 1
                archive_record_id = self._record_archive(
                    archive_url=archive_url,
                    payload=payload,
                    sha256=sha256,
                    result=result,
                    source_day=source_day,
                    status="downloaded",
                )
                xml_results = process_zip_payload(payload)
                if existing_archive is not None and existing_archive.status == "processed":
                    result.archives_unchanged += 1
                result.xml_count += len(xml_results)
                for item in xml_results:
                    if item.status != "parsed" or item.tender is None:
                        result.failed_count += 1
                        if item.error:
                            result.errors.append({"file": item.file_name, "message": item.error})
                        continue
                    result.parsed_count += 1
                    state = self._persist_tender(item.tender, source_archive_id=archive_record_id)
                    if state == "inserted":
                        result.records_inserted += 1
                    elif state == "updated":
                        result.records_updated += 1
                    else:
                        result.records_unchanged += 1
                self._record_archive(
                    archive_url=archive_url,
                    payload=payload,
                    sha256=sha256,
                    result=result,
                    source_day=source_day,
                    status="processed",
                    xml_count=len(xml_results),
                    error_summary="; ".join(err["message"] for err in result.errors[-5:]) or None,
                )
            except Exception as exc:  # noqa: BLE001
                result.failed_count += 1
                result.errors.append({"archive_url_hash": _sha256_text(archive_url), "message": str(exc)})
        return result

    def _download_archive_bytes(self, archive_url: str, target_dir: Path) -> bytes:
        downloaded = self.client.download_archive(archive_url, target_dir)
        return (target_dir / downloaded.stored_name).read_bytes()

    def _record_archive(
        self,
        *,
        archive_url: str,
        payload: bytes,
        sha256: str,
        result: BulkFetchResult,
        source_day: date,
        status: str,
        xml_count: int = 0,
        error_summary: str | None = None,
    ) -> str | None:
        if self.repository is None:
            return None
        archive, _created = self.repository.upsert_source_archive(
            {
                "source": PROVIDER,
                "region_code": result.region,
                "source_date": source_day,
                "subsystem_type": result.subsystem,
                "document_type": result.document_type,
                "archive_url_hash": _sha256_text(archive_url),
                "archive_name": Path(urlparse(archive_url).path).name or "archive.zip",
                "sha256": sha256,
                "size_bytes": len(payload),
                "xml_count": xml_count,
                "downloaded_at": utcnow(),
                "processed_at": utcnow() if status == "processed" else None,
                "status": status,
                "error_summary": error_summary,
            }
        )
        return archive.id

    def _persist_tender(self, tender: dict, *, source_archive_id: str | None) -> str:
        if self.repository is None:
            return "unchanged"
        _record, state = self.repository.upsert_tender_with_version(tender, source_archive_id=source_archive_id)
        return state


def process_zip_payload(payload: bytes) -> list[ParsedXmlResult]:
    results: list[ParsedXmlResult] = []
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = [item for item in archive.infolist() if not item.is_dir()]
        if len(members) > MAX_ZIP_FILES:
            raise ValueError(f"ZIP has too many files: {len(members)}")
        total_unpacked = sum(item.file_size for item in members)
        if total_unpacked > MAX_ZIP_UNPACKED_BYTES:
            raise ValueError("ZIP unpacked payload exceeds safety limit")
        for item in members:
            entry = Path(item.filename)
            if entry.is_absolute() or ".." in entry.parts:
                results.append(ParsedXmlResult(item.filename, "failed", error="unsafe zip path"))
                continue
            if _is_zip_symlink(item):
                results.append(ParsedXmlResult(item.filename, "failed", error="symlink zip entry rejected"))
                continue
            if entry.suffix.lower() != ".xml":
                continue
            if item.file_size > MAX_XML_BYTES:
                results.append(ParsedXmlResult(item.filename, "failed", error="XML file exceeds safety limit"))
                continue
            try:
                xml_bytes = archive.read(item)
                tender = parse_ep_notification_xml(xml_bytes, file_name=item.filename)
                results.append(ParsedXmlResult(item.filename, "parsed", tender=tender))
            except Exception as exc:  # noqa: BLE001
                results.append(ParsedXmlResult(item.filename, "failed", error=str(exc)))
    return results


def parse_ep_notification_xml(xml_bytes: bytes, *, file_name: str = "") -> dict:
    if b"<!DOCTYPE" in xml_bytes[:1000].upper() or b"<!ENTITY" in xml_bytes[:1000].upper():
        raise ValueError("XML contains forbidden DTD/entity declarations")
    root = ET.fromstring(xml_bytes)
    purchase_number = _first_text(root, "purchaseNumber")
    if not purchase_number:
        raise ValueError("purchaseNumber not found")
    title = _first_text(root, "purchaseObjectInfo")
    raw = {
        "file_name": file_name,
        "purchase_number": purchase_number,
        "publish_dt_in_eis": _first_text(root, "publishDTInEIS"),
        "purchase_object_info": title,
        "customer_name": _customer_name(root),
        "customer_inn": _first_text(root, "INN", "inn"),
        "nmck": _first_float(_first_text(root, "maxPrice", "initialSum", "price")),
        "currency": _first_text(root, "currencyCode", "currency") or "RUB",
        "application_deadline": _first_text(root, "endDate", "endDT", "submissionCloseDateTime"),
        "placing_way": _placing_way(root),
        "okpd2": _all_texts(root, "OKPD2", "okpd2", "OKPD2Code"),
        "href": _first_text(root, "href"),
        "scheme_version": root.find(".//*").attrib.get("schemeVersion") if root.find(".//*") is not None else None,
        "version_number": _first_text(root, "versionNumber"),
        "modification_date": _first_text(root, "modificationDate", "updateDate", "publishDTInEIS"),
    }
    normalized = {
        "source": PROVIDER,
        "external_id": purchase_number,
        "registry_number": purchase_number,
        "purchase_number": purchase_number,
        "law_type": "44-ФЗ",
        "title": title or purchase_number,
        "description": title,
        "customer_name": raw["customer_name"],
        "customer_inn": raw["customer_inn"],
        "region": None,
        "eis_url": raw["href"],
        "nmck_amount": raw["nmck"],
        "currency": raw["currency"],
        "publication_date": _parse_datetime(raw["publish_dt_in_eis"]),
        "application_deadline": _parse_datetime(raw["application_deadline"]),
        "status": _first_text(root, "state", "status"),
        "raw_payload": raw,
    }
    normalized["content_hash"] = content_hash(json.dumps(raw, sort_keys=True, ensure_ascii=False))
    return normalized


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _first_text(node: ET.Element, *names: str) -> str | None:
    lowered = {name.lower() for name in names}
    for child in node.iter():
        if _local_name(child.tag).lower() in lowered and child.text and child.text.strip():
            return child.text.strip()
    return None


def _all_texts(node: ET.Element, *names: str) -> list[str]:
    lowered = {name.lower() for name in names}
    return [child.text.strip() for child in node.iter() if _local_name(child.tag).lower() in lowered and child.text and child.text.strip()]


def _first_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _customer_name(root: ET.Element) -> str | None:
    for node in root.iter():
        if _local_name(node.tag).lower() in {"customer", "responsibleorg", "purchaseorganization"}:
            value = _first_text(node, "fullName", "shortName", "name")
            if value:
                return value
    return _first_text(root, "fullName")


def _placing_way(root: ET.Element) -> str | None:
    for node in root.iter():
        if _local_name(node.tag) == "placingWay":
            return _first_text(node, "name", "code")
    return None


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_zip_symlink(info: zipfile.ZipInfo) -> bool:
    return ((info.external_attr >> 16) & 0o170000) == 0o120000


def _parse_exact_date(value: str) -> date:
    return date.fromisoformat(value[:10])
