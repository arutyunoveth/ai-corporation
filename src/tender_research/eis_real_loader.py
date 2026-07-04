from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from src.modules.tender_operator_agent_demo.procurement_schemas import (
    ProcurementSearchRequest,
)
from src.modules.tender_operator_agent_demo.settings import (
    get_zakupki_soap_settings,
)
from src.modules.tender_operator_agent_demo.zakupki_soap_client import (
    ZakupkiSoapClient,
)
from src.tender_research.errors import EisLoaderError
from src.tender_research.schemas import EisDocumentRaw, EisTenderRaw

logger = logging.getLogger(__name__)


class RealEisLoader:
    def __init__(self, soap_client: ZakupkiSoapClient | None = None):
        self._client = soap_client or self._build_client()

    @staticmethod
    def _build_client() -> ZakupkiSoapClient:
        settings = get_zakupki_soap_settings()
        if not settings.configured:
            logger.warning(
                "ZakupkiSoapSettings not configured (token missing or disabled). "
                "EIS SOAP calls will fail."
            )
        return ZakupkiSoapClient(settings)

    # ── Public API (matches EisTenderLoader interface) ──

    def fetch_tenders(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        law_type: str | None = None,
        query: str | None = None,
    ) -> list[EisTenderRaw]:
        raw_results = self._search_procurements(
            date_from=date_from,
            date_to=date_to,
            limit=limit,
            law_type=law_type,
            query=query,
        )
        tenders: list[EisTenderRaw] = []
        for r in raw_results:
            try:
                tenders.append(self._result_to_raw(r))
            except Exception as e:
                logger.error("Failed to normalize search result %s: %s", r.procurement_id, e)
        return tenders

    def fetch_tender_details(self, external_id: str) -> EisTenderRaw | None:
        if not self._client.is_configured():
            logger.warning("EIS SOAP not configured, cannot fetch details for %s", external_id)
            return None
        try:
            details = self._client.get_procurement_details(external_id)
            raw = self._result_to_raw(details.procurement)
            docs = self._attachments_to_raw(details.attachments)
            raw.documents = docs
            return raw
        except Exception as e:
            logger.error("Failed to fetch details for %s: %s", external_id, e)
            return None

    def fetch_tender_documents(self, tender: EisTenderRaw) -> list[EisDocumentRaw]:
        if not self._client.is_configured():
            return []
        try:
            attachments = self._client.list_attachments(tender.external_id)
            return self._attachments_to_raw(attachments)
        except Exception as e:
            logger.error("Failed to fetch documents for %s: %s", tender.external_id, e)
            return []

    # ── Internal helpers ──

    def _search_procurements(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int | None = None,
        law_type: str | None = None,
        query: str | None = None,
    ) -> list:
        if not self._client.is_configured():
            logger.warning("EIS SOAP not configured, returning empty search results")
            return []
        req = ProcurementSearchRequest(
            source="zakupki_gov_ru_soap_legacy",
            query=query or "",
            law=law_type,
            date_from=date_from.isoformat() if date_from else None,
            date_to=date_to.isoformat() if date_to else None,
            max_results=limit or 20,
        )
        try:
            return self._client.search_procurements(req)
        except Exception as e:
            logger.error("EIS SOAP search failed: %s", e)
            return []

    def _result_to_raw(self, r) -> EisTenderRaw:
        try:
            pub_date = self._parse_dt(r.publication_date)
            deadline = self._parse_dt(r.deadline)
        except Exception:
            pub_date = None
            deadline = None

        nmck = r.initial_price
        if nmck is not None:
            nmck = float(nmck)

        return EisTenderRaw(
            external_id=r.procurement_id,
            title=r.title,
            customer_name=r.customer_name,
            customer_inn=r.customer_inn,
            law_type=r.law,
            nmck_amount=nmck,
            currency=r.currency or "RUB",
            publication_date=pub_date,
            application_deadline=deadline,
            status=r.status,
            registry_number=r.registry_number,
            purchase_number=r.notice_number,
            eis_url=r.source_url,
            raw_payload=r.model_dump(mode="json") if hasattr(r, "model_dump") else None,
        )

    def _attachments_to_raw(self, attachments: list) -> list[EisDocumentRaw]:
        return [
            EisDocumentRaw(
                file_name=a.name,
                file_url=a.url,
                source_document_id=a.attachment_id,
                content_type=a.content_type,
                size_bytes=a.size_bytes,
            )
            for a in attachments
            if a.name
        ]

    @staticmethod
    def _parse_dt(value: str | None) -> datetime | None:
        if not value:
            return None
        for fmt in (
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S%z",
            "%Y-%m-%d",
            "%d.%m.%Y",
            "%d.%m.%Y %H:%M",
            "%Y/%m/%d",
        ):
            try:
                return datetime.strptime(value, fmt)
            except ValueError:
                continue
        try:
            from datetime import timezone
            return datetime.fromisoformat(value)
        except Exception:
            return None
