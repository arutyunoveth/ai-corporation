from __future__ import annotations

from urllib.parse import urlencode, urlparse


ALLOWED_44FZ_HOSTS = (
    "zakupki.gov.ru",
    "www.zakupki.gov.ru",
)

EIS_44FZ_SEARCH_PATH = "/epz/order/extendedsearch/results.html"


def build_44fz_search_url(
    query: str,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    max_results: int = 10,
) -> str:
    if not query or not query.strip():
        raise ValueError("Поисковый запрос не может быть пустым.")
    params = {
        "searchString": query.strip(),
        "morphology": "on",
        "sortDirection": "false",
    }
    if region and region.strip():
        params["regionDeleted"] = "false"
        params["region"] = region.strip()
    if date_from:
        params["publishDateFrom"] = date_from
    if date_to:
        params["publishDateTo"] = date_to
    if price_from is not None:
        params["priceFrom"] = str(price_from)
    if price_to is not None:
        params["priceTo"] = str(price_to)
    params["recordsPerPage"] = str(min(max(max_results, 1), 50))
    return f"https://zakupki.gov.ru{EIS_44FZ_SEARCH_PATH}?{urlencode(params)}"


def normalize_44fz_search_params(
    query: str | None = None,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    max_results: int | None = None,
) -> dict[str, str]:
    normalized: dict[str, str] = {}
    if query and query.strip():
        normalized["searchString"] = query.strip()
    else:
        raise ValueError("Поисковый запрос не может быть пустым.")
    if region and region.strip():
        normalized["region"] = region.strip()
    if date_from:
        normalized["publishDateFrom"] = date_from
    if date_to:
        normalized["publishDateTo"] = date_to
    if price_from is not None:
        normalized["priceFrom"] = str(price_from)
    if price_to is not None:
        normalized["priceTo"] = str(price_to)
    if max_results is not None:
        normalized["recordsPerPage"] = str(min(max(max_results, 1), 50))
    return normalized


def validate_public_eis_url(url: str) -> bool:
    if not url:
        return False
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return False
    hostname = (parsed.hostname or "").lower()
    if not any(hostname == host or hostname.endswith(f".{host}") for host in ALLOWED_44FZ_HOSTS):
        return False
    if not parsed.path.startswith(EIS_44FZ_SEARCH_PATH):
        return False
    return True
