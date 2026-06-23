from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Callable
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener, urlopen
from xml.etree import ElementTree as ET

from src.modules.tender_operator_agent_demo.procurement_schemas import (
    ProcurementAttachment,
    ProcurementDetails,
    ProcurementSearchRequest,
    ProcurementSearchResult,
)
from src.modules.tender_operator_agent_demo.settings import ZakupkiSoapSettings
from src.modules.tender_operator_agent_demo.zakupki_soap_templates import (
    build_attachments_envelope,
    build_details_envelope,
    build_search_envelope,
)


SoapTransport = Callable[[str, str | None, int], str]
MAX_XML_CHARS = 5_000_000


class ZakupkiSoapClient:
    def __init__(self, settings: ZakupkiSoapSettings, transport: SoapTransport | None = None) -> None:
        self.settings = settings
        self._transport = transport

    def is_configured(self) -> bool:
        return self.settings.configured

    def search_procurements(self, request: ProcurementSearchRequest) -> list[ProcurementSearchResult]:
        if not self.is_configured():
            return []
        envelope = build_search_envelope(request, self.settings.token)
        xml = self._post_soap(envelope, soap_action=self.settings.search_action)
        return parse_search_response(xml)[: self.settings.max_results]

    def get_procurement_details(self, procurement_id: str) -> ProcurementDetails:
        if not self.is_configured():
            raise RuntimeError("Источник ЕИС не настроен для получения карточки закупки.")
        envelope = build_details_envelope(procurement_id, self.settings.token)
        return parse_details_response(self._post_soap(envelope, soap_action=self.settings.details_action))

    def list_attachments(self, procurement_id: str) -> list[ProcurementAttachment]:
        if not self.is_configured():
            return []
        envelope = build_attachments_envelope(procurement_id, self.settings.token)
        return parse_attachments_response(self._post_soap(envelope, soap_action=self.settings.attachments_action))[
            : self.settings.max_attachments
        ]

    def download_attachment(self, attachment: ProcurementAttachment, target_dir: Path):
        raise RuntimeError("Скачивание вложений выполняется через attachment_downloader.")

    def _post_soap(self, envelope: str, soap_action: str | None = None) -> str:
        if not self.is_configured():
            raise RuntimeError("Источник ЕИС не настроен для SOAP-запросов.")
        self._write_debug_artifact("last_request.xml", _sanitize_xml(envelope, self.settings.token))
        try:
            if self._transport is not None:
                xml = self._transport(envelope, soap_action, self.settings.timeout_seconds)
            else:
                xml = self._default_transport(envelope, soap_action)
            self._write_debug_artifact("last_response.xml", _sanitize_xml(xml, self.settings.token))
            return xml
        except Exception as exc:  # noqa: BLE001
            message = _sanitize_error(str(exc), self.settings.token)
            self._write_debug_artifact("last_error.txt", message)
            raise RuntimeError(f"SOAP-запрос к ЕИС завершился ошибкой: {message}") from None

    def _default_transport(self, envelope: str, soap_action: str | None) -> str:
        headers = {
            "Content-Type": "text/xml; charset=utf-8",
            "User-Agent": "ai-corporation-tender-demo/1.0",
        }
        if soap_action:
            headers["SOAPAction"] = soap_action
        request = Request(
            self.settings.base_url,
            data=envelope.encode("utf-8"),
            headers=headers,
            method="POST",
        )
        try:
            if self.settings.trust_env_proxy:
                response = urlopen(request, timeout=self.settings.timeout_seconds)
            else:
                opener = build_opener(ProxyHandler({}))
                response = opener.open(request, timeout=self.settings.timeout_seconds)
            with response:
                return response.read().decode("utf-8", errors="replace")
        except HTTPError as exc:
            raise RuntimeError(f"HTTP {exc.code}") from exc
        except URLError as exc:
            raise RuntimeError(str(exc.reason)) from exc

    def _write_debug_artifact(self, name: str, content: str) -> None:
        if not self.settings.debug:
            return
        target_dir = Path(os.environ.get("AI_CORP_ZAKUPKI_SOAP_DIAGNOSTICS_DIR", "company_agent_runs/zakupki_soap_live_diagnostics"))
        target_dir.mkdir(parents=True, exist_ok=True)
        (target_dir / name).write_text(content, encoding="utf-8")


def parse_search_response(xml: str) -> list[ProcurementSearchResult]:
    root = _safe_parse_xml(xml)
    results: list[ProcurementSearchResult] = []
    for node in _candidate_nodes(root, {"procurement", "purchase", "notice"}):
        procurement_id = _first_text(node, "procurement_id", "procurementId", "id", "guid")
        title = _first_text(node, "title", "name", "purchaseName", "subject")
        customer_name = _first_text(node, "customer_name", "customerName", "customer", "organizationName")
        source_url = _first_text(node, "source_url", "sourceUrl", "url", "href")
        if not procurement_id or not title:
            continue
        attachments_count = _to_int(_first_text(node, "attachments_count", "attachmentsCount", "documentsCount")) or 0
        can_download = attachments_count > 0
        warnings: list[str] = []
        notice_number = _first_text(node, "notice_number", "noticeNumber", "purchaseNumber")
        if not customer_name:
            warnings.append("Не удалось извлечь заказчика из SOAP-ответа.")
        if not source_url:
            warnings.append("Ссылка на карточку не сформирована: формат URL требует уточнения.")
        if not _first_text(node, "law", "fz", "lawName"):
            warnings.append("Не удалось определить закон закупки из SOAP-ответа.")
        results.append(
            ProcurementSearchResult(
                procurement_id=procurement_id,
                notice_number=notice_number,
                registry_number=_first_text(node, "registry_number", "registryNumber"),
                title=title,
                customer_name=customer_name or "Не указан",
                customer_inn=_first_text(node, "customer_inn", "customerInn", "inn"),
                law=_first_text(node, "law", "fz", "lawName"),
                source="zakupki_gov_ru_soap",
                source_url=source_url or "https://zakupki.gov.ru/",
                publication_date=_parse_date_text(_first_text(node, "publication_date", "publicationDate", "publishDate")),
                deadline=_parse_date_text(_first_text(node, "deadline", "endDate", "submissionDeadline")),
                initial_price=_to_float(_first_text(node, "initial_price", "initialPrice", "maxPrice")),
                currency=_first_text(node, "currency", "currencyCode") or "RUB",
                status=_first_text(node, "status", "state", "statusName"),
                attachments_count=attachments_count,
                attachments_status="downloadable" if can_download else "manual_upload_required",
                can_download_attachments=can_download,
                requires_manual_upload=not can_download,
                warnings=warnings,
            )
        )
    return results


def parse_details_response(xml: str) -> ProcurementDetails:
    root = _safe_parse_xml(xml)
    results = parse_search_response(xml)
    warnings: list[str] = []
    if results:
        procurement = results[0]
    else:
        warnings.append("SOAP details method не дал нормализованный procurement node; используется partial fallback.")
        procurement = ProcurementSearchResult(
            procurement_id=_first_text(root, "procurement_id", "procurementId", "id") or "unknown",
            notice_number=_first_text(root, "notice_number", "noticeNumber", "purchaseNumber"),
            registry_number=_first_text(root, "registry_number", "registryNumber"),
            title=_first_text(root, "title", "name", "purchaseName", "subject") or "Закупка без названия",
            customer_name=_first_text(root, "customer_name", "customerName", "customer") or "Не указан",
            law=_first_text(root, "law", "fz", "lawName"),
            source="zakupki_gov_ru_soap",
            source_url=_first_text(root, "source_url", "sourceUrl", "url", "href") or "https://zakupki.gov.ru/",
            attachments_count=0,
            attachments_status="manual_upload_required",
            can_download_attachments=False,
            requires_manual_upload=True,
            warnings=["Использован partial details fallback."],
        )
    return ProcurementDetails(
        procurement=procurement,
        attachments=parse_attachments_response(xml),
        raw_source_summary=_first_text(root, "description", "summary"),
        warnings=warnings + procurement.warnings,
    )


def parse_attachments_response(xml: str) -> list[ProcurementAttachment]:
    root = _safe_parse_xml(xml)
    attachments: list[ProcurementAttachment] = []
    for node in _candidate_nodes(root, {"attachment", "document", "file"}):
        name = _first_text(node, "name", "fileName", "filename", "documentName")
        attachment_id = _first_text(node, "attachment_id", "attachmentId", "id", "fileId", "documentId", "docId")
        if not name:
            continue
        url = _first_text(node, "url", "downloadUrl", "href")
        warnings: list[str] = []
        if not url and attachment_id:
            warnings.append("В ответе ЕИС есть идентификатор документа, но нет прямой ссылки на скачивание.")
        attachments.append(
            ProcurementAttachment(
                attachment_id=attachment_id or name,
                name=name,
                url=url,
                content_type=_first_text(node, "content_type", "contentType", "mimeType"),
                size_bytes=_to_int(_first_text(node, "size_bytes", "sizeBytes", "fileSize")),
                extension=_extension_from_name(name),
                can_download=bool(url),
                requires_manual_upload=not bool(url),
                warnings=warnings or ([] if url else ["В ответе ЕИС нет ссылки на скачивание."]),
            )
        )
    return attachments


def _safe_parse_xml(xml: str) -> ET.Element:
    if len(xml) > MAX_XML_CHARS:
        raise ValueError("SOAP XML response is too large")
    lowered = xml[:1000].lower()
    if "<!doctype" in lowered or "<!entity" in lowered:
        raise ValueError("SOAP XML response contains forbidden DTD or entity declarations")
    return ET.fromstring(xml)


def _sanitize_error(message: str, token: str) -> str:
    if token:
        message = message.replace(token, "[redacted]")
    return message


def _sanitize_xml(xml: str, token: str) -> str:
    if token:
        xml = xml.replace(token, "[redacted]")
    return xml


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _candidate_nodes(root: ET.Element, names: set[str]) -> list[ET.Element]:
    return [node for node in root.iter() if _local_name(node.tag) in names]


def _first_text(node: ET.Element, *names: str) -> str | None:
    lowered = {name.lower() for name in names}
    for child in node.iter():
        if _local_name(child.tag).lower() in lowered and child.text and child.text.strip():
            return child.text.strip()
    return None


def _to_int(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        return int(float(value.replace(" ", "").replace(",", ".")))
    except ValueError:
        return None


def _to_float(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _parse_date_text(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d.%m.%Y", "%d.%m.%Y %H:%M", "%Y/%m/%d"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return text


def _extension_from_name(name: str) -> str | None:
    if "." not in name:
        return None
    return "." + name.rsplit(".", 1)[-1].lower()
