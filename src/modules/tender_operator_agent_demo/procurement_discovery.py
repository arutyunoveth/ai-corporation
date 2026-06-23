from __future__ import annotations

from src.modules.tender_operator_agent_demo.procurement_sources import (
    DemoProcurementRecord,
    get_demo_local_procurements,
    get_procurement_source_descriptors,
)
from src.modules.tender_operator_agent_demo.procurement_schemas import (
    ProcurementAttachment,
    ProcurementDetails,
    ProcurementSearchRequest as ProcurementSearchRequestV2,
    ProcurementSearchResult as ProcurementSearchResultV2,
    ProcurementSourceStatus,
)
from src.modules.tender_operator_agent_demo.schemas import ProcurementSearchResponse, ProcurementSearchResult
from src.modules.tender_operator_agent_demo.settings import get_zakupki_soap_settings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import ZakupkiSoapClient


def list_procurement_sources() -> list[ProcurementSourceStatus]:
    zakupki_settings = get_zakupki_soap_settings()
    zakupki_status = zakupki_settings.safe_status()
    return [
        ProcurementSourceStatus(
            source="demo_local",
            label="demo_local",
            enabled=True,
            configured=True,
            reason=None,
            safe_diagnostics={"mode": "offline_demo"},
        ),
        ProcurementSourceStatus(
            source="zakupki_gov_ru_soap",
            label="zakupki_gov_ru_soap",
            enabled=zakupki_settings.enabled,
            configured=zakupki_settings.configured,
            reason=zakupki_status["reason"],
            safe_diagnostics=zakupki_status,
        ),
    ]


def _matches_text(record: DemoProcurementRecord, query: str) -> bool:
    if not query.strip():
        return True
    haystack = " ".join(
        [
            record.title,
            record.category,
            record.customer_name,
            record.procurement_number,
            record.summary,
            record.region,
        ]
    ).lower()
    return all(token in haystack for token in query.lower().split())


def _matches_optional(value: str | None, query: str | None) -> bool:
    if not query:
        return True
    return query.lower() in (value or "").lower()


def _matches_price(record: DemoProcurementRecord, price_from: float | None, price_to: float | None) -> bool:
    if record.initial_price is None:
        return price_from is None
    if price_from is not None and record.initial_price < price_from:
        return False
    if price_to is not None and record.initial_price > price_to:
        return False
    return True


def _matches_date(value: str | None, date_from: str | None, date_to: str | None) -> bool:
    if not value:
        return True
    if date_from and value < date_from:
        return False
    if date_to and value > date_to:
        return False
    return True


def _to_result(record: DemoProcurementRecord) -> ProcurementSearchResult:
    return ProcurementSearchResult(
        procurement_id=record.procurement_id,
        source=record.source,
        title=record.title,
        procurement_number=record.procurement_number,
        customer_name=record.customer_name,
        category=record.category,
        publication_date=record.publication_date,
        deadline=record.deadline,
        initial_price=record.initial_price,
        currency=record.currency,
        region=record.region,
        source_url=record.source_url,
        attachments_status=record.attachments_status,
        attachments_count=len(record.attachments),
        available_attachments_count=len(record.attachments),
        summary=record.summary,
        attachment_names=[item.name for item in record.attachments],
        source_note=record.source_note,
    )


def _to_search_result_v2(record: DemoProcurementRecord) -> ProcurementSearchResultV2:
    can_download = bool(record.attachments)
    return ProcurementSearchResultV2(
        procurement_id=record.procurement_id,
        notice_number=record.procurement_number,
        registry_number=record.procurement_number,
        title=record.title,
        customer_name=record.customer_name,
        customer_inn=None,
        law="44-ФЗ",
        source=record.source,
        source_url=record.source_url,
        publication_date=record.publication_date,
        deadline=record.deadline,
        initial_price=record.initial_price,
        currency=record.currency,
        status="demo",
        attachments_count=len(record.attachments),
        attachments_status=record.attachments_status,
        can_download_attachments=can_download,
        requires_manual_upload=not can_download,
        warnings=[] if can_download else ["Автоматическое получение документации недоступно в demo_local."],
    )


def _search_demo_local_v2(request: ProcurementSearchRequestV2) -> list[ProcurementSearchResultV2]:
    records: list[ProcurementSearchResultV2] = []
    for item in get_demo_local_procurements():
        if not _matches_text(item, request.query):
            continue
        if not _matches_optional(item.customer_name, request.customer_name):
            continue
        if request.customer_inn:
            continue
        if request.law and request.law not in {"Все", "44-ФЗ"}:
            continue
        if not _matches_optional(item.region, request.region):
            continue
        if not _matches_price(item, request.price_from, request.price_to):
            continue
        if not _matches_date(item.publication_date, request.date_from, request.date_to):
            continue
        records.append(_to_search_result_v2(item))
    return records[: request.max_results]


def search_procurements(
    request: ProcurementSearchRequestV2 | None = None,
    *,
    query: str = "",
    source: str = "demo_local",
    max_results: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
    customer_name: str | None = None,
    region: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
) -> ProcurementSearchResponse | list[ProcurementSearchResultV2]:
    if request is not None:
        sources = {item.source: item for item in list_procurement_sources()}
        if request.source not in sources:
            raise ValueError(f"Unknown procurement source: {request.source}")
        if request.source == "demo_local":
            return _search_demo_local_v2(request)
        if request.source == "zakupki_gov_ru_soap":
            if not sources[request.source].configured:
                return []
            return ZakupkiSoapClient(get_zakupki_soap_settings()).search_procurements(request)
        return []

    descriptors = get_procurement_source_descriptors()
    allowed_sources = {item.code: item for item in descriptors}
    if source not in allowed_sources:
        raise ValueError(f"Unknown procurement source: {source}")
    if not allowed_sources[source].enabled:
        return ProcurementSearchResponse(
            query=query,
            source=source,
            results=[],
            sources=descriptors,
            warnings=[allowed_sources[source].note or "Источник временно недоступен в demo-контуре."],
        )
    if source != "demo_local":
        return ProcurementSearchResponse(
            query=query,
            source=source,
            results=[],
            sources=descriptors,
            warnings=["В текущем спринте включён только offline-safe источник demo_local."],
        )

    records = []
    for item in get_demo_local_procurements():
        if not _matches_text(item, query):
            continue
        if not _matches_optional(item.customer_name, customer_name):
            continue
        if not _matches_optional(item.region, region):
            continue
        if not _matches_price(item, price_from, price_to):
            continue
        if not _matches_date(item.publication_date, date_from, date_to):
            continue
        records.append(_to_result(item))

    return ProcurementSearchResponse(
        query=query,
        source=source,
        results=records[: max(1, min(max_results, 20))],
        sources=descriptors,
        warnings=[],
    )


def get_demo_procurement(source: str, procurement_id: str) -> DemoProcurementRecord | None:
    if source != "demo_local":
        return None
    for item in get_demo_local_procurements():
        if item.procurement_id == procurement_id:
            return item
    return None


def get_procurement_details(source: str, procurement_id: str) -> ProcurementDetails:
    sources = {item.source for item in list_procurement_sources()}
    if source not in sources:
        raise ValueError(f"Unknown procurement source: {source}")
    if source == "zakupki_gov_ru_soap":
        settings = get_zakupki_soap_settings()
        if not settings.configured:
            raise ValueError("Источник ЕИС не настроен: добавьте ZAKUPKI_GOV_RU_SOAP_TOKEN в .env.local")
        return ZakupkiSoapClient(settings).get_procurement_details(procurement_id)
    record = get_demo_procurement(source, procurement_id)
    if record is None:
        raise ValueError("Procurement was not found")
    attachments = [
        ProcurementAttachment(
            attachment_id=f"{record.procurement_id}-ATT-{index:02d}",
            name=item.name,
            url=None,
            content_type=item.content_type,
            size_bytes=len(item.payload),
            extension="." + item.name.rsplit(".", 1)[-1].lower() if "." in item.name else None,
            can_download=True,
            requires_manual_upload=False,
        )
        for index, item in enumerate(record.attachments, start=1)
    ]
    return ProcurementDetails(
        procurement=_to_search_result_v2(record),
        attachments=attachments,
        raw_source_summary=record.summary,
        warnings=[],
    )
