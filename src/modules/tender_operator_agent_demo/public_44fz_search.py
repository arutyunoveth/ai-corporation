from __future__ import annotations

from datetime import datetime

from src.tender_research.providers.public_44fz_search import (
    EIS_44FZ_HOST,
    EIS_44FZ_SEARCH_PATH,
    LAW_FLAGS,
    Public44FzSearchProvider,
    _normalize_law,
)

ALLOWED_44FZ_HOSTS = (
    "zakupki.gov.ru",
    "www.zakupki.gov.ru",
)

EIS_44FZ_SEARCH_PATH = EIS_44FZ_SEARCH_PATH
PUBLIC_EIS_LAW_FLAGS = dict(LAW_FLAGS)

Public44FzSearchProvider = Public44FzSearchProvider
normalize_public_eis_law = _normalize_law

PUBLIC_EIS_STAGE_FLAGS = {
    "подача заявок": "af",
    "работа комиссии": "ca",
    "закупка завершена": "pc",
    "закупка отменена": "pa",
}


def resolve_public_eis_stage_flag(status_filter: str | None) -> str | None:
    if not status_filter or not status_filter.strip():
        return None
    return PUBLIC_EIS_STAGE_FLAGS.get(status_filter.strip().lower())


def _normalize_public_eis_date(value: str | None) -> str | None:
    if not value or not value.strip():
        return None
    cleaned = value.strip()
    for fmt in ("%Y-%m-%d", "%d.%m.%Y"):
        try:
            parsed = datetime.strptime(cleaned, fmt)
            return parsed.strftime("%d.%m.%Y")
        except ValueError:
            continue
    return cleaned


def _build_public_eis_search_params(
    *,
    query: str,
    law: str = "44fz",
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    status_filter: str | None = None,
    page: int | None = None,
    max_results: int | None = None,
) -> dict[str, str]:
    normalized_law = _normalize_law(law)
    if not query or not query.strip():
        raise ValueError("Поисковый запрос не может быть пустым.")
    params = {
        "searchString": query.strip(),
        "morphology": "on",
        "sortDirection": "false",
        LAW_FLAGS[normalized_law]: "on",
    }
    if region and region.strip():
        params["regionDeleted"] = "false"
        params["region"] = region.strip()
    normalized_date_from = _normalize_public_eis_date(date_from)
    normalized_date_to = _normalize_public_eis_date(date_to)
    if normalized_date_from:
        params["publishDateFrom"] = normalized_date_from
    if normalized_date_to:
        params["publishDateTo"] = normalized_date_to
    if price_from is not None:
        params["priceFromGeneral"] = str(price_from)
    if price_to is not None:
        params["priceToGeneral"] = str(price_to)
    stage_flag = resolve_public_eis_stage_flag(status_filter)
    if stage_flag:
        params[stage_flag] = "on"
    if page is not None:
        params["pageNumber"] = str(max(page, 1))
    if max_results is not None:
        params["recordsPerPage"] = str(min(max(max_results, 1), 50))
    return params


def build_public_eis_search_url(
    query: str,
    *,
    law: str = "44fz",
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    status_filter: str | None = None,
    page: int = 1,
    max_results: int = 10,
) -> str:
    params = _build_public_eis_search_params(
        query=query,
        law=law,
        region=region,
        date_from=date_from,
        date_to=date_to,
        price_from=price_from,
        price_to=price_to,
        status_filter=status_filter,
        page=page,
        max_results=max_results,
    )
    return f"https://zakupki.gov.ru{EIS_44FZ_SEARCH_PATH}?{urlencode(params)}"


def build_44fz_search_url(
    query: str,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    status_filter: str | None = None,
    page: int = 1,
    max_results: int = 10,
) -> str:
    return build_public_eis_search_url(
        query,
        law="44fz",
        region=region,
        date_from=date_from,
        date_to=date_to,
        price_from=price_from,
        price_to=price_to,
        status_filter=status_filter,
        page=page,
        max_results=max_results,
    )


def normalize_44fz_search_params(
    query: str | None = None,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    status_filter: str | None = None,
    page: int | None = None,
    max_results: int | None = None,
) -> dict[str, str]:
    return _build_public_eis_search_params(
        query=query or "",
        law="44fz",
        region=region,
        date_from=date_from,
        date_to=date_to,
        price_from=price_from,
        price_to=price_to,
        status_filter=status_filter,
        page=page,
        max_results=max_results,
    )


def validate_public_eis_url(url: str) -> bool:
    if not url:
        return False
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    if not any(hostname == host or hostname.endswith(f".{host}") for host in ALLOWED_44FZ_HOSTS):
        return False
    if not parsed.path.startswith(EIS_44FZ_SEARCH_PATH):
        return False
    return True


from urllib.parse import urlencode
