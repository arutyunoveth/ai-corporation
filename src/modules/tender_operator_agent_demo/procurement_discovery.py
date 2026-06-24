from __future__ import annotations

import json
import os
from pathlib import Path
from urllib.parse import urlencode, urlparse

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
from src.modules.tender_operator_agent_demo.relevance_scoring import score_procurement_card
from src.modules.tender_operator_agent_demo.schemas import ProcurementSearchResponse, ProcurementSearchResult, PublicSearchUrlResponse
from src.modules.tender_operator_agent_demo.supplier_profile import SupplierProfile
from src.modules.tender_operator_agent_demo.public_44fz_parser import (
    Public44FzSearchStatus,
    classify_public_search_response,
    fetch_public_44fz_search_page,
    parse_44fz_search_results,
)
from src.modules.tender_operator_agent_demo.public_44fz_search import build_44fz_search_url
from src.modules.tender_operator_agent_demo.settings import get_zakupki_soap_settings
from src.modules.tender_operator_agent_demo.zakupki_soap_client import ZakupkiSoapClient


def _diagnostics_dir() -> Path:
    configured = os.environ.get("AI_CORP_ZAKUPKI_SOAP_DIAGNOSTICS_DIR")
    if configured:
        return Path(configured)
    new_default = Path("company_agent_runs/zakupki_soap_diagnostics")
    old_default = Path("company_agent_runs/zakupki_soap_live_diagnostics")
    return new_default if new_default.exists() or not old_default.exists() else old_default


def _load_zakupki_live_diagnostics() -> dict[str, object]:
    status_path = _diagnostics_dir() / "last_status.json"
    if status_path.is_file():
        try:
            payload = json.loads(status_path.read_text(encoding="utf-8"))
            return {
                "endpoint_host": payload.get("endpoint_host", ""),
                "endpoint_path": payload.get("endpoint_path", ""),
                "last_status": payload.get("last_status", ""),
                "last_error": payload.get("last_error", ""),
                "soap_action": payload.get("soap_action", ""),
                "method_name": payload.get("method_name", ""),
                "token_owner": payload.get("token_owner", ""),
                "mode": payload.get("mode", ""),
            }
        except Exception:
            return {}
    return {}


def list_procurement_sources() -> list[ProcurementSourceStatus]:
    zakupki_settings = get_zakupki_soap_settings()
    zakupki_status = zakupki_settings.safe_status()
    parsed = urlparse(zakupki_settings.active_docs_endpoint)
    live_diagnostics = _load_zakupki_live_diagnostics()
    getdocs_reason = zakupki_status["reason"] or "Токен физлица найден. getDocsIP настроен для read-only получения документации."
    return [
        ProcurementSourceStatus(
            source="demo_local",
            label="Демо-набор (локальный)",
            enabled=True,
            configured=True,
            reason=None,
            safe_diagnostics={"mode": "offline_demo"},
        ),
        ProcurementSourceStatus(
            source="public_eis_html_44fz",
            label="Публичный поиск ЕИС 44-ФЗ",
            enabled=True,
            configured=True,
            reason="Публичный HTML fallback. Поиск и выбор закупки выполняются вручную в ЕИС.",
            safe_diagnostics={"mode": "public_html_fallback", "law": "44fz"},
        ),
        ProcurementSourceStatus(
            source="public_eis_html_223fz",
            label="Публичный поиск ЕИС 223-ФЗ (fallback)",
            enabled=True,
            configured=True,
            reason="Публичный HTML fallback. Для 223-ФЗ требуется отдельный parser path.",
            safe_diagnostics={"mode": "public_html_fallback", "law": "223fz"},
        ),
        ProcurementSourceStatus(
            source="zakupki_gov_ru_getdocs_ip",
            label="zakupki_gov_ru_getdocs_ip",
            enabled=zakupki_settings.enabled,
            configured=zakupki_settings.configured,
            reason=getdocs_reason,
            safe_diagnostics={
                **zakupki_status,
                "token_present": zakupki_settings.token_configured,
                "endpoint_host": parsed.hostname or "",
                "endpoint_path": parsed.path or "/",
                **live_diagnostics,
            },
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
        if request.source in {"public_eis_html_44fz", "public_eis_html_223fz", "zakupki_gov_ru_getdocs_ip"}:
            return []
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
            warnings=[allowed_sources[source].note or "Поиск выполняется вручную через публичный HTML fallback."],
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


_current_supplier_profile: SupplierProfile | None = None


def get_supplier_profile() -> SupplierProfile:
    global _current_supplier_profile
    if _current_supplier_profile is None:
        _current_supplier_profile = SupplierProfile.load_demo_fixture()
    return _current_supplier_profile


def reset_supplier_profile() -> SupplierProfile:
    global _current_supplier_profile
    _current_supplier_profile = SupplierProfile.load_demo_fixture()
    return _current_supplier_profile


def set_supplier_profile(profile: SupplierProfile) -> None:
    global _current_supplier_profile
    _current_supplier_profile = profile


def search_public_44fz(
    query: str,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    max_results: int = 10,
) -> dict:
    try:
        url = build_44fz_search_url(
            query=query,
            region=region,
            date_from=date_from,
            date_to=date_to,
            price_from=price_from,
            price_to=price_to,
            max_results=max_results,
        )
    except ValueError as exc:
        return {
            "status": "validation_error",
            "cards": [],
            "eis_search_url": None,
            "error": str(exc),
            "parser_status": Public44FzSearchStatus.MANUAL_OPEN_REQUIRED,
        }

    fetch_result = fetch_public_44fz_search_page(url)
    parser_status = fetch_result.get("status", Public44FzSearchStatus.NETWORK_ERROR)

    if parser_status != Public44FzSearchStatus.PARSED or not fetch_result.get("html"):
        return {
            "status": parser_status,
            "cards": [],
            "eis_search_url": url,
            "error": fetch_result.get("error"),
            "parser_status": parser_status,
        }

    cards = parse_44fz_search_results(fetch_result["html"])
    profile = get_supplier_profile()
    scored_cards = []
    for card in cards[:max_results]:
        result = score_procurement_card(
            title=card.get("title", ""),
            initial_price=card.get("initial_price"),
            customer_name=card.get("customer_name"),
            profile=profile,
        )
        card_with_relevance = dict(card)
        card_with_relevance["relevance"] = result.to_dict()
        scored_cards.append(card_with_relevance)

    return {
        "status": Public44FzSearchStatus.PARSED if cards else Public44FzSearchStatus.UNSUPPORTED_LAYOUT,
        "cards": scored_cards,
        "eis_search_url": url,
        "error": None,
        "parser_status": Public44FzSearchStatus.PARSED if cards else Public44FzSearchStatus.UNSUPPORTED_LAYOUT,
    }


def build_public_search_url(
    *,
    query: str,
    law: str,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> PublicSearchUrlResponse:
    normalized_law = "223fz" if law.lower() == "223fz" else "44fz"
    base_url = (
        "https://zakupki.gov.ru/epz/order223/extendedsearch/results.html"
        if normalized_law == "223fz"
        else "https://zakupki.gov.ru/epz/order/extendedsearch/results.html"
    )
    params = {
        "searchString": query,
        "morphology": "on",
        "sortDirection": "false",
    }
    if region:
        params["regionDeleted"] = "false"
        params["region"] = region
    if date_from:
        params["publishDateFrom"] = date_from
    if date_to:
        params["publishDateTo"] = date_to
    return PublicSearchUrlResponse(
        source=f"public_eis_html_{normalized_law}",
        law=normalized_law,
        query=query,
        eis_search_url=f"{base_url}?{urlencode(params)}",
        note="Откройте ЕИС, выберите закупку и вставьте реестровый номер в поле getDocsIP.",
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
    if source == "zakupki_gov_ru_getdocs_ip":
        raise ValueError("getDocsIP не используется как поиск карточки. Сначала найдите закупку публично, затем запросите документацию по номеру.")
    if source in {"public_eis_html_44fz", "public_eis_html_223fz"}:
        raise ValueError("Для public HTML fallback карточка закупки открывается вручную в ЕИС.")
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
