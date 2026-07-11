from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from src.modules.tender_operator_agent_demo.live_pipeline_service import (
    build_line_items_from_spec_rows,
    download_live_documents,
    extract_document_texts,
    fetch_live_card_details,
    parse_line_items_from_texts,
)
from src.modules.tender_operator_agent_demo.procurement_discovery import (
    get_demo_local_procurements,
    get_procurement_details,
    search_procurements,
    search_public_44fz,
)
from src.modules.tender_operator_agent_demo.procurement_schemas import (
    ProcurementSearchRequest as ProcurementSearchRequestV2,
)
from src.modules.tender_operator_agent_demo.procurement_sources import (
    get_demo_local_procurements,
)
from src.modules.tender_operator_agent_demo.schemas import (
    LineItem,
    ResellerDecisionLabel,
    ResellerSearchAndTriageResponse,
    ResellerSearchRequest,
    ResellerSearchResponse,
    ResellerTenderSearchResult,
    ResellerTriageReport,
    SourceType,
    StopFactor,
    StopFactorSeverity,
    TenderCard,
    TotalCountKind,
)
from src.modules.tender_operator_agent_demo.upload_service import (
    _collect_documents,
    _collect_role_text,
    _dedupe_text_items,
)


SEARCH_FRESHEN_NOTICE = (
    "Для экономии времени анализируется одна закупка — самая свежая из результатов поиска."
)
ANALYSIS_LIMIT_NOTICE = (
    "За один цикл анализируется только самая свежая закупка из результатов поиска."
)


def _parse_date(value: str | None) -> datetime | None:
    if not value:
        return None
    cleaned = value.strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d.%m.%Y %H:%M", "%d.%m.%Y"):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    return None


def select_freshest_tender(results: list[ResellerTenderSearchResult]) -> tuple[ResellerTenderSearchResult | None, str | None]:
    if not results:
        return None, None

    dated_count = sum(1 for r in results if _parse_date(r.publication_date) is not None)
    total = len(results)

    if dated_count == 0:
        results[0].is_freshest = True
        return results[0], "date_unavailable_first_result"

    best = results[0]
    best_date = _parse_date(best.publication_date)

    for item in results[1:]:
        item_date = _parse_date(item.publication_date)
        if item_date is None:
            continue
        if best_date is None or item_date > best_date:
            best = item
            best_date = item_date

    best.is_freshest = True

    if dated_count < total:
        return best, "date_mixed_selected_latest_dated"

    return best, "date_available_selected_latest"


def _search_demo_local(request: ResellerSearchRequest) -> ResellerSearchResponse:
    records = get_demo_local_procurements()
    results: list[ResellerTenderSearchResult] = []
    query_lower = request.query.lower().strip()

    for item in records:
        if query_lower:
            haystack = " ".join([
                item.title, item.category, item.customer_name,
                item.procurement_number or "", item.summary, item.region or "",
            ]).lower()
            if query_lower not in haystack:
                continue

        if request.region and item.region and request.region.lower() not in item.region.lower():
            continue
        if request.price_from is not None and item.initial_price is not None:
            if item.initial_price < request.price_from:
                continue
        if request.price_to is not None and item.initial_price is not None:
            if item.initial_price > request.price_to:
                continue
        if request.date_from and item.publication_date:
            if item.publication_date < request.date_from:
                continue
        if request.date_to and item.publication_date:
            if item.publication_date > request.date_to:
                continue

        law_label = "44-ФЗ"
        if item.source_note and "223" in item.source_note:
            law_label = "223-ФЗ"

        results.append(ResellerTenderSearchResult(
            procurement_id=item.procurement_id,
            title=item.title,
            customer_name=item.customer_name,
            initial_price=item.initial_price,
            currency=item.currency,
            publication_date=item.publication_date,
            deadline=item.deadline,
            region=item.region,
            law=law_label,
            source_url=item.source_url,
        ))

    if request.max_results and len(results) > request.max_results:
        results = results[:request.max_results]

    total_results = len(results)
    freshest, selection_reason = select_freshest_tender(results)

    return ResellerSearchResponse(
        query=request.query,
        filters=request.model_dump(exclude={"query", "max_results", "source", "customer_mode"}, exclude_none=True),
        total_results=total_results,
        total_results_label=f"Найдено закупок: {total_results}",
        total_count_kind=TotalCountKind.EXACT,
        results=results,
        freshest=freshest,
        selection_reason=selection_reason,
        is_fallback=False,
        fallback_used=False,
        source_type=SourceType.DEMO,
        source_label="Демо-набор (локальный)",
        source_notice="Это демонстрационный набор данных, а не live-поиск. Используется для проверки сценария, когда источник поиска недоступен.",
        synthetic_used=True,
    )


def _customer_search_unavailable_response(request: ResellerSearchRequest) -> ResellerSearchResponse:
    return ResellerSearchResponse(
        query=request.query,
        filters=request.model_dump(exclude={"query", "max_results", "source", "customer_mode"}, exclude_none=True),
        total_results=None,
        total_results_label=None,
        total_count_kind=TotalCountKind.UNAVAILABLE,
        results=[],
        freshest=None,
        selection_reason=None,
        is_fallback=False,
        fallback_used=False,
        source_type=SourceType.LIVE,
        source_label="Публичный поиск закупок",
        source_notice="Реальный поиск закупок сейчас недоступен. Проверьте источник поиска или повторите позже.",
        search_unavailable=True,
        synthetic_used=False,
    )


def _search_public_44fz(request: ResellerSearchRequest) -> ResellerSearchResponse:
    try:
        result = search_public_44fz(
            query=request.query,
            law="44fz",
            region=request.region,
            date_from=request.date_from,
            date_to=request.date_to,
            price_from=request.price_from,
            price_to=request.price_to,
            max_results=request.max_results or 10,
        )
    except Exception:
        if request.customer_mode:
            return _customer_search_unavailable_response(request)
        return _fallback_search(request, source_unavailable=True)

    cards = result.get("cards", [])
    if not cards or result.get("parser_status") != "parsed":
        if request.customer_mode:
            return _customer_search_unavailable_response(request)
        return _fallback_search(request, source_unavailable=True)

    results: list[ResellerTenderSearchResult] = []
    for card in cards:
        results.append(ResellerTenderSearchResult(
            procurement_id=card.get("procurement_id", card.get("registry_number", "")),
            title=card.get("title", ""),
            customer_name=card.get("customer_name", ""),
            initial_price=card.get("initial_price"),
            currency=card.get("currency", "RUB"),
            publication_date=card.get("publication_date"),
            deadline=card.get("deadline"),
            region=card.get("region"),
            law="44-ФЗ",
            source_url=card.get("source_url", ""),
        ))

    total_results = len(cards)
    total_label = f"Найдено минимум {total_results} результатов" if total_results > 0 else "Найдено закупок: 0"

    freshest, selection_reason = select_freshest_tender(results)

    return ResellerSearchResponse(
        query=request.query,
        filters=request.model_dump(exclude={"query", "max_results", "source", "customer_mode"}, exclude_none=True),
        total_results=total_results,
        total_results_label=total_label,
        total_count_kind=TotalCountKind.LOWER_BOUND,
        results=results,
        freshest=freshest,
        selection_reason=selection_reason,
        is_fallback=False,
        fallback_used=False,
        source_type=SourceType.LIVE,
        source_label="Публичный поиск ЕИС 44-ФЗ",
        source_notice=None,
        search_unavailable=False,
        synthetic_used=False,
    )


def _fallback_search(
    request: ResellerSearchRequest,
    source_unavailable: bool = False,
) -> ResellerSearchResponse:
    records = get_demo_local_procurements()
    results: list[ResellerTenderSearchResult] = []

    for item in records:
        results.append(ResellerTenderSearchResult(
            procurement_id=item.procurement_id,
            title=item.title,
            customer_name=item.customer_name,
            initial_price=item.initial_price,
            currency=item.currency,
            publication_date=item.publication_date,
            deadline=item.deadline,
            region=item.region,
            law="44-ФЗ",
            source_url=item.source_url,
        ))

    total_results = len(results)
    freshest, selection_reason = select_freshest_tender(results)

    fallback_label = "Источник поиска временно недоступен. Показан демонстрационный набор данных."

    return ResellerSearchResponse(
        query=request.query,
        filters=request.model_dump(exclude={"query", "max_results", "source", "customer_mode"}, exclude_none=True),
        total_results=total_results,
        total_results_label=fallback_label,
        total_count_kind=TotalCountKind.SHOWN_COUNT,
        results=results,
        freshest=freshest,
        selection_reason=selection_reason,
        is_fallback=True,
        fallback_label=fallback_label,
        fallback_used=True,
        source_type=SourceType.DEMO,
        source_label="Источник поиска временно недоступен",
        source_notice=fallback_label,
        synthetic_used=True,
    )


def search_tenders(request: ResellerSearchRequest) -> ResellerSearchResponse:
    if request.customer_mode:
        return _search_public_44fz(request)
    if request.source == "demo_local":
        return _search_demo_local(request)
    if request.source == "public_eis_html_44fz":
        return _search_public_44fz(request)
    return _fallback_search(request)


def _fetch_tender_details(
    procurement_id: str,
    source: str,
    search_result: ResellerTenderSearchResult | None = None,
) -> dict[str, Any]:
    if source != "demo_local" and search_result is not None:
        return {
            "title": search_result.title,
            "procurement_id": search_result.procurement_id,
            "notice_number": search_result.procurement_id,
            "customer_name": search_result.customer_name,
            "customer_inn": None,
            "law": search_result.law or "44-ФЗ",
            "initial_price": search_result.initial_price,
            "currency": search_result.currency or "RUB",
            "publication_date": search_result.publication_date,
            "deadline": search_result.deadline,
            "region": search_result.region,
            "status": None,
            "attachments_count": 0,
            "attachments_status": "live_search",
            "warnings": [],
            "raw_source_summary": None,
            "delivery_place": None,
            "delivery_terms": None,
            "source_url": search_result.source_url,
            "attachments": [],
        }
    try:
        details = get_procurement_details(source, procurement_id)
        procurement = details.procurement
        return {
            "title": procurement.title,
            "procurement_id": procurement_id,
            "notice_number": procurement.notice_number,
            "customer_name": procurement.customer_name,
            "customer_inn": procurement.customer_inn,
            "law": procurement.law,
            "initial_price": procurement.initial_price,
            "currency": procurement.currency or "RUB",
            "publication_date": procurement.publication_date,
            "deadline": procurement.deadline,
            "region": procurement.region if hasattr(procurement, "region") else None,
            "status": procurement.status,
            "attachments_count": procurement.attachments_count,
            "attachments_status": procurement.attachments_status,
            "warnings": procurement.warnings,
            "raw_source_summary": details.raw_source_summary,
            "delivery_place": None,
            "delivery_terms": None,
            "attachments": [
                {
                    "name": a.name,
                    "extension": a.extension,
                    "can_download": a.can_download,
                }
                for a in details.attachments
            ],
        }
    except Exception:
        return {
            "title": procurement_id,
            "procurement_id": procurement_id,
            "notice_number": None,
            "customer_name": None,
            "customer_inn": None,
            "law": None,
            "initial_price": None,
            "currency": "RUB",
            "publication_date": None,
            "deadline": None,
            "region": None,
            "status": None,
            "attachments_count": 0,
            "attachments_status": "unavailable_in_demo",
            "warnings": ["Детали закупки недоступны"],
            "raw_source_summary": None,
            "delivery_place": None,
            "delivery_terms": None,
            "attachments": [],
        }


def _score_tender_match(details: dict[str, Any]) -> int:
    score = 25
    title = (details.get("title") or "").lower()
    if any(kw in title for kw in ("поставка", "товар", "оборудован", "кабель", "материал")):
        score = 25
    elif any(kw in title for kw in ("услуг", "работ")):
        score = 15
    return min(score, 25)


def _score_spec_clarity(details: dict[str, Any]) -> int:
    attachments = details.get("attachments", [])
    if not attachments:
        return 0
    has_spec = any(
        "spec" in (a.get("name", "") or "").lower()
        or "тз" in (a.get("name", "") or "").lower()
        or "техни" in (a.get("name", "") or "").lower()
        for a in attachments
    )
    if has_spec:
        return 15
    return 5


def _score_commercial_potential(details: dict[str, Any]) -> int:
    price = details.get("initial_price")
    if price is None:
        return 5
    if price >= 10_000_000:
        return 20
    if price >= 3_000_000:
        return 15
    if price >= 500_000:
        return 10
    return 5


def _score_deadline(details: dict[str, Any]) -> int:
    deadline = details.get("deadline")
    pub_date = details.get("publication_date")
    if not deadline or not pub_date:
        return 5
    d = _parse_date(deadline)
    p = _parse_date(pub_date)
    if not d or not p:
        return 5
    delta = (d - p).days
    if delta >= 30:
        return 15
    if delta >= 14:
        return 10
    if delta >= 7:
        return 5
    return 0


def _score_documents(details: dict[str, Any]) -> int:
    status = details.get("attachments_status", "")
    count = details.get("attachments_count", 0)
    if "downloadable" in status or "available" in status:
        return 15 if count >= 3 else 10
    if "manual" in status:
        return 5
    return 0


def _score_contract_risks(details: dict[str, Any]) -> int:
    return 10


def _detect_stop_factors(details: dict[str, Any]) -> list[StopFactor]:
    factors: list[StopFactor] = []
    title_lower = (details.get("title") or "").lower()
    summary = (details.get("raw_source_summary") or "").lower()
    combined = f"{title_lower} {summary}"

    if any(kw in combined for kw in ("лиценз", "сро", "допуск", "свидетельство о допуске")):
        factors.append(StopFactor(
            code="license_sro_required",
            title="Лицензия / СРО / специальный допуск",
            severity=StopFactorSeverity.CRITICAL,
            evidence="Обнаружено упоминание лицензии или СРО",
            source="text_analysis",
        ))

    if any(kw in combined for kw in ("только производител", "производител", "authorized")):
        factors.append(StopFactor(
            code="manufacturer_only",
            title="Признаки «только производитель»",
            severity=StopFactorSeverity.CRITICAL,
            evidence="Обнаружено ограничение по производителю",
            source="text_analysis",
        ))

    deadline = details.get("deadline")
    pub_date = details.get("publication_date")
    if deadline and pub_date:
        d = _parse_date(deadline)
        p = _parse_date(pub_date)
        if d and p:
            delta = (d - p).days
            if delta < 7 and delta > 0:
                factors.append(StopFactor(
                    code="short_deadline",
                    title="Короткий срок до подачи",
                    severity=StopFactorSeverity.WARNING,
                    evidence=f"Срок подачи: {delta} дней с даты публикации",
                    source="date_analysis",
                ))

    if any(kw in combined for kw in ("обеспечение заявк", "обеспечение контракт", "обеспечение исполнения")):
        factors.append(StopFactor(
            code="security_required",
            title="Обеспечение заявки / контракта",
            severity=StopFactorSeverity.WARNING,
            evidence="Обнаружено требование обеспечения",
            source="text_analysis",
        ))

    if any(kw in combined for kw in ("смп", "сонко", "субъект малого", "малое предпринимател")):
        factors.append(StopFactor(
            code="smp_restriction",
            title="Ограничения по СМП/СОНКО",
            severity=StopFactorSeverity.INFO,
            evidence="Обнаружена пометка о СМП/СОНКО",
            source="text_analysis",
        ))

    if any(kw in combined for kw in ("национальн", "происхожден", "запрет", "страна происхождения", "постановление")):
        factors.append(StopFactor(
            code="national_regime",
            title="Национальный режим / ограничения происхождения",
            severity=StopFactorSeverity.WARNING,
            evidence="Обнаружены ограничения по происхождению товара",
            source="text_analysis",
        ))

    if any(kw in combined for kw in ("сертификат", "декларация соответствия", "паспорт качеств")):
        factors.append(StopFactor(
            code="certificates_required",
            title="Сертификаты / декларации / паспорта качества",
            severity=StopFactorSeverity.INFO,
            evidence="Требуется подтверждение сертификатов",
            source="text_analysis",
        ))

    if any(kw in combined for kw in ("аналог", "эквивалент", "импортозамещен")):
        factors.append(StopFactor(
            code="analogs_unclear",
            title="Запрет или неясность аналогов",
            severity=StopFactorSeverity.WARNING,
            evidence="Упоминание аналогов или импортозамещения",
            source="text_analysis",
        ))

    attachments = details.get("attachments", [])
    if not attachments:
        factors.append(StopFactor(
            code="no_line_items",
            title="Не удалось извлечь позиции поставки",
            severity=StopFactorSeverity.WARNING,
            evidence="Нет доступных вложений с документацией",
            source="attachment_analysis",
        ))

    return factors


def _build_tender_card(details: dict[str, Any]) -> TenderCard:
    return TenderCard(
        tender_id=details.get("procurement_id") or details.get("notice_number") or "",
        title=details.get("title", ""),
        customer=details.get("customer_name", ""),
        law_type=details.get("law"),
        source=details.get("attachments_status"),
        nmck=details.get("initial_price"),
        currency=details.get("currency", "RUB"),
        publication_date=details.get("publication_date"),
        submission_deadline=details.get("deadline"),
        region=details.get("region"),
        delivery_place=details.get("delivery_place"),
        delivery_terms=details.get("delivery_terms"),
        source_url=details.get("source_url"),
    )


def _build_line_items(details: dict[str, Any]) -> list[LineItem]:
    items: list[LineItem] = []
    attachments = details.get("attachments", [])
    for att in attachments:
        name = (att.get("name") or "").lower()
        if any(kw in name for kw in ("spec", "тз", "техни", "позиц", "line")):
            items.append(LineItem(
                item_name=att.get("name", ""),
                evidence="Из вложения: " + (att.get("name", "")),
            ))
    return items


def _determine_completeness(
    details_status: str,
    documents_count: int,
    downloaded_count: int,
    parsed_count: int,
    line_items_count: int,
) -> str:
    if line_items_count > 0:
        return "line_items_extracted"
    if parsed_count > 0:
        return "documents_parsed"
    if downloaded_count > 0:
        return "documents_loaded"
    if details_status == "loaded":
        return "details_loaded"
    return "search_only"


def _build_user_visible_limitations(
    completeness: str,
    documents_status: str,
    details_status: str,
) -> list[str]:
    limitations: list[str] = []
    if completeness == "search_only":
        limitations.append("Доступны только данные поисковой выдачи. Для полноценного решения нужны документы закупки.")
    if details_status == "partial":
        limitations.append("Карточка закупки загружена частично.")
    if documents_status in ("not_requested", "failed"):
        limitations.append("Документы закупки не удалось получить автоматически.")
    if completeness == "documents_parsed" and details_status != "loaded":
        limitations.append("Позиции поставки требуют ручной проверки.")
    limitations.append("Для финального решения нужны закупочные цены, логистика и условия поставщиков.")
    return limitations


def _enrich_with_live_details(details: dict[str, Any]) -> dict[str, Any]:
    if details.get("attachments_status") != "live_search":
        return details
    enriched = dict(details)
    card_details, details_status = fetch_live_card_details(
        ResellerTenderSearchResult(
            procurement_id=details.get("procurement_id", ""),
            title=details.get("title", ""),
            customer_name=details.get("customer_name", ""),
            initial_price=details.get("initial_price"),
            publication_date=details.get("publication_date"),
            deadline=details.get("deadline"),
            region=details.get("region"),
            law=details.get("law"),
            source_url=details.get("source_url"),
        )
    )
    enriched["_details_status"] = details_status
    enriched["_documents_count"] = 0
    enriched["_downloaded_count"] = 0
    enriched["_parsed_count"] = 0

    if card_details:
        enriched["title"] = card_details.get("title") or enriched.get("title", "")
        enriched["customer_name"] = card_details.get("customer_name") or enriched.get("customer_name", "")
        if card_details.get("initial_price") is not None:
            enriched["initial_price"] = card_details["initial_price"]
        if card_details.get("publication_date"):
            enriched["publication_date"] = card_details["publication_date"]
        if card_details.get("deadline"):
            enriched["deadline"] = card_details["deadline"]
        enriched["source_url"] = card_details.get("source_url") or enriched.get("source_url", "")
        enriched["_details_status"] = "loaded" if details_status == "loaded" else "partial"

        doc_links = card_details.get("live_document_links", [])
        enriched["_documents_count"] = len(doc_links)

        if doc_links:
            dl_result = download_live_documents(doc_links)
            enriched["_downloaded_count"] = dl_result.get("downloaded_count", 0)
            enriched["_documents_status"] = dl_result.get("status", "not_found")

            files = dl_result.get("files", [])
            if files:
                texts = extract_document_texts(files)
                enriched["_parsed_count"] = len(texts)
                if texts:
                    spec_rows = parse_line_items_from_texts(texts)
                    line_items_dicts = build_line_items_from_spec_rows(spec_rows)
                    if line_items_dicts:
                        enriched["_spec_line_items"] = line_items_dicts

    return enriched


def analyze_tender_for_reseller(
    procurement_id: str,
    source: str,
    source_type: SourceType = SourceType.UNKNOWN,
    source_label: str | None = None,
    source_notice: str | None = None,
    search_result: ResellerTenderSearchResult | None = None,
) -> ResellerTriageReport:
    details = _fetch_tender_details(procurement_id, source, search_result=search_result)

    if source_type == SourceType.LIVE and details.get("attachments_status") == "live_search":
        details = _enrich_with_live_details(details)

    details_status = details.pop("_details_status", "search_only")
    doc_count = details.pop("_documents_count", 0)
    dl_count = details.pop("_downloaded_count", 0)
    parsed_count = details.pop("_parsed_count", 0)
    doc_status = details.pop("_documents_status", "not_requested")
    spec_line_items = details.pop("_spec_line_items", None)

    completeness = _determine_completeness(details_status, doc_count, dl_count, parsed_count, spec_line_items is not None)

    product_score = _score_tender_match(details)
    spec_score = _score_spec_clarity(details)
    commercial_score = _score_commercial_potential(details)
    deadline_score = _score_deadline(details)
    docs_score = _score_documents(details)
    risk_score = _score_contract_risks(details)

    total_score = product_score + spec_score + commercial_score + deadline_score + docs_score + risk_score
    total_score = min(max(total_score, 0), 100)

    if completeness in ("search_only", "details_loaded"):
        if total_score > 74:
            total_score = 74
    elif completeness == "documents_parsed":
        if total_score > 74:
            total_score = 74

    stop_factors = _detect_stop_factors(details)

    has_critical = any(f.severity == StopFactorSeverity.CRITICAL for f in stop_factors)
    has_no_line_items = any(sf.code == "no_line_items" for sf in stop_factors)
    insufficient_data = details.get("attachments_count", 0) == 0 and not details.get("raw_source_summary")

    if completeness == "search_only":
        if not any(sf.code == "no_line_items" for sf in stop_factors):
            stop_factors.append(StopFactor(
                code="no_line_items",
                title="Не удалось извлечь позиции поставки",
                severity=StopFactorSeverity.WARNING,
                evidence="Доступны только данные поисковой выдачи",
                source="completeness_analysis",
            ))
            has_no_line_items = True

    reasons: list[str] = []

    if insufficient_data and completeness == "search_only":
        decision_label = ResellerDecisionLabel.NEEDS_REVIEW
        if total_score > 50:
            total_score = 50
        reasons.append("Недостаточно данных для полного анализа закупки")
        reasons.append("Требуется ручная загрузка документов")
    elif has_critical:
        decision_label = ResellerDecisionLabel.NO_GO
        if total_score > 34:
            total_score = 34
        reasons.append("Обнаружены критические стоп-факторы, исключающие участие")
        for sf in stop_factors:
            if sf.severity == StopFactorSeverity.CRITICAL:
                reasons.append(f"Стоп-фактор: {sf.title}")
    elif completeness == "search_only":
        decision_label = ResellerDecisionLabel.NEEDS_REVIEW
        if total_score > 74:
            total_score = 74
        reasons.append("Доступны только данные поисковой выдачи. Для полного анализа нужны документы закупки.")
    elif completeness in ("details_loaded", "documents_parsed"):
        decision_label = ResellerDecisionLabel.NEEDS_REVIEW
        if total_score > 74:
            total_score = 74
        reasons.append("Позиции поставки не извлечены из документов. Требуется ручная проверка.")
        reasons.append(f"Скоринг скорректирован: {total_score}/100")
    elif has_no_line_items and total_score >= 55:
        decision_label = ResellerDecisionLabel.NEEDS_REVIEW
        if total_score > 74:
            total_score = 74
        reasons.append("Не удалось извлечь позиции поставки — требуется ручная проверка")
        reasons.append(f"Скоринг скорректирован: {total_score}/100")
    elif total_score >= 75:
        decision_label = ResellerDecisionLabel.GO
        reasons.append("Закупка соответствует критериям отбора")
        reasons.append(f"Общий скоринг: {total_score}/100")
    elif total_score >= 55:
        decision_label = ResellerDecisionLabel.NEEDS_REVIEW
        reasons.append("Закупка требует дополнительной проверки")
        reasons.append(f"Скоринг в зоне неопределённости: {total_score}/100")
    elif total_score >= 35:
        decision_label = ResellerDecisionLabel.LOW_PRIORITY
        reasons.append("Закупка имеет низкий приоритет")
        reasons.append(f"Скоринг: {total_score}/100")
    else:
        decision_label = ResellerDecisionLabel.NO_GO
        reasons.append("Закупка не соответствует минимальным критериям отбора")

    stop_factor_titles = [sf.title for sf in stop_factors]
    reseller_summary = (
        f"Закупка: {details.get('title', 'Не указана')}. "
        f"Заказчик: {details.get('customer_name', 'Не указан')}. "
        f"НМЦК: {_format_price(details.get('initial_price'))}."
    )
    if stop_factor_titles:
        reseller_summary += f" Выявлены стоп-факторы: {'; '.join(stop_factor_titles[:3])}."
    if decision_label == ResellerDecisionLabel.GO:
        reseller_summary += " Закупка предварительно одобрена."
    elif decision_label == ResellerDecisionLabel.NO_GO:
        reseller_summary += " Закупка не рекомендуется к участию."
    else:
        reseller_summary += " Требуется дополнительная проверка."

    limitations = _build_user_visible_limitations(completeness, doc_status, details_status)
    commercial_note = limitations[-1]

    manager_recommendation = _build_manager_recommendation(decision_label, stop_factors, details)

    tender_card = _build_tender_card(details)
    line_items = _build_line_items(details)

    if spec_line_items:
        line_items = [LineItem(**li) for li in spec_line_items]
    elif line_items:
        pass

    is_fallback = source_type == SourceType.DEMO
    fallback_label = source_notice if is_fallback else None

    return ResellerTriageReport(
        decision_label=decision_label,
        decision_score=total_score,
        decision_reasons=reasons,
        stop_factors=stop_factors,
        reseller_summary=reseller_summary,
        manager_recommendation=manager_recommendation + " " + commercial_note,
        analysis_limit_notice=ANALYSIS_LIMIT_NOTICE,
        is_fallback=is_fallback,
        fallback_label=fallback_label,
        source_type=source_type,
        source_label=source_label,
        source_notice=source_notice,
        tender_card=tender_card,
        line_items=line_items,
        has_line_items=len(line_items) > 0,
        export_report_url=None,
        details_status=details_status,
        documents_status=doc_status,
        analysis_completeness=completeness,
        documents_count=doc_count,
        downloaded_documents_count=dl_count,
        parsed_documents_count=parsed_count,
        line_items_count=len(line_items),
    )


def _format_price(price: float | None) -> str:
    if price is None:
        return "Не указана"
    return f"{price:,.2f} ₽".replace(",", " ")


def _build_manager_recommendation(
    decision: ResellerDecisionLabel,
    stop_factors: list[StopFactor],
    details: dict[str, Any],
) -> str:
    if decision == ResellerDecisionLabel.GO:
        return "Рекомендуется принять закупку в работу. Запросить коммерческие предложения и уточнить логистику."
    elif decision == ResellerDecisionLabel.NO_GO:
        critical_factors = [sf.title for sf in stop_factors if sf.severity == StopFactorSeverity.CRITICAL]
        if critical_factors:
            return f"Закупка не рекомендуется. Критические стоп-факторы: {'; '.join(critical_factors)}."
        return "Закупка не рекомендуется к участию по совокупности факторов."
    elif decision == ResellerDecisionLabel.LOW_PRIORITY:
        warnings = [sf.title for sf in stop_factors if sf.severity == StopFactorSeverity.WARNING]
        if warnings:
            return f"Закупка низкого приоритета. Рекомендуется проверка факторов: {'; '.join(warnings)}."
        return "Закупка может быть отложена. Рекомендуется проверить коммерческие условия."
    else:
        return "Требуется ручная проверка закупки. Проверить документы, стоп-факторы и коммерческие условия."


def run_search_and_triage(request: ResellerSearchRequest) -> ResellerSearchAndTriageResponse:
    search_response = search_tenders(request)

    if search_response.search_unavailable:
        return ResellerSearchAndTriageResponse(
            search=search_response,
            triage=None,
            analysis_limit_notice="Реальный поиск закупок сейчас недоступен.",
            status="search_unavailable",
            synthetic_used=False,
        )

    if not search_response.results or not search_response.freshest:
        return ResellerSearchAndTriageResponse(
            search=search_response,
            triage=None,
            analysis_limit_notice=SEARCH_FRESHEN_NOTICE,
            status="no_results",
            synthetic_used=search_response.synthetic_used,
        )

    if request.customer_mode and search_response.source_type != SourceType.LIVE:
        return ResellerSearchAndTriageResponse(
            search=search_response,
            triage=None,
            analysis_limit_notice="Клиентский режим анализирует только реальные закупки.",
            status="search_unavailable",
            synthetic_used=False,
        )

    freshest = search_response.freshest
    triage = analyze_tender_for_reseller(
        freshest.procurement_id,
        request.source,
        source_type=search_response.source_type,
        source_label=search_response.source_label,
        source_notice=search_response.source_notice,
        search_result=freshest,
    )

    return ResellerSearchAndTriageResponse(
        search=search_response,
        triage=triage,
        analysis_limit_notice=SEARCH_FRESHEN_NOTICE,
        status="completed",
        synthetic_used=search_response.synthetic_used,
    )
