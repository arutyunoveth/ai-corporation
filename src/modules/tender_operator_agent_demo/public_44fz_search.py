from __future__ import annotations

from urllib.parse import urlencode, urlparse


ALLOWED_44FZ_HOSTS = (
    "zakupki.gov.ru",
    "www.zakupki.gov.ru",
)

EIS_44FZ_SEARCH_PATH = "/epz/order/extendedsearch/results.html"

PUBLIC_EIS_LAW_FLAGS = {
    "44fz": "fz44",
    "223fz": "fz223",
    "capital_repair": "ppRf615",
}


def normalize_public_eis_law(law: str | None) -> str:
    normalized = (law or "44fz").strip().lower().replace("-", "").replace("_", "")
    if normalized in {"44фз", "44fz", "44"}:
        return "44fz"
    if normalized in {"223фз", "223fz", "223"}:
        return "223fz"
    if normalized in {"капремонт", "капрем", "capitalrepair", "615", "pp615", "pprf615", "615pp"}:
        return "capital_repair"
    raise ValueError("Поддерживаются только категории 44-ФЗ, 223-ФЗ и капремонт.")


def _build_public_eis_search_params(
    *,
    query: str,
    law: str = "44fz",
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
    max_results: int | None = None,
) -> dict[str, str]:
    normalized_law = normalize_public_eis_law(law)
    if not query or not query.strip():
        raise ValueError("Поисковый запрос не может быть пустым.")
    params = {
        "searchString": query.strip(),
        "morphology": "on",
        "sortDirection": "false",
        PUBLIC_EIS_LAW_FLAGS[normalized_law]: "on",
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
        max_results=max_results,
    )


def normalize_44fz_search_params(
    query: str | None = None,
    region: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    price_from: float | None = None,
    price_to: float | None = None,
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
        max_results=max_results,
    )


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
