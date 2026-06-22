from __future__ import annotations

from src.modules.tender_operator_agent_demo.procurement_sources import (
    DemoProcurementRecord,
    get_demo_local_procurements,
    get_procurement_source_descriptors,
)
from src.modules.tender_operator_agent_demo.schemas import ProcurementSearchResponse, ProcurementSearchResult


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


def search_procurements(
    *,
    query: str,
    source: str,
    max_results: int = 10,
    date_from: str | None = None,
    date_to: str | None = None,
    customer_name: str | None = None,
    region: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
) -> ProcurementSearchResponse:
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
