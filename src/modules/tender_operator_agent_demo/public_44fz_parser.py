from __future__ import annotations

from src.tender_research.providers.public_44fz_search import (
    MAX_RESPONSE_BYTES,
    PublicSearchStatus,
    PublicTenderSearchItem,
    PublicTenderSearchPage,
    Public44FzSearchProvider,
    _classify_search_html,
    _extract_price,
    _extract_first_date,
    _extract_procedure_type,
    _extract_reestr_from_card,
    _extract_reestr_from_text,
    _extract_between,
    _extract_label_value_pairs,
    _extract_registry_body_pairs,
    _fallback_extract_by_number_patterns,
    _first_matching_value,
    _normalize_law,
    _parse_single_entry,
    _split_registry_entries,
    _strip_html,
    parse_44fz_search_results,
)

Public44FzSearchStatus = PublicSearchStatus
PublicTenderSearchItem = PublicTenderSearchItem
PublicTenderSearchPage = PublicTenderSearchPage
Public44FzSearchProvider = Public44FzSearchProvider

# Backward-compatible classifier
classify_public_search_response = _classify_search_html

# Backward-compatible fetcher (uses shared provider under the hood)
_default_provider: Public44FzSearchProvider | None = None


def _get_provider() -> Public44FzSearchProvider:
    global _default_provider
    if _default_provider is None:
        _default_provider = Public44FzSearchProvider(bypass_proxy=True)
    return _default_provider


def fetch_public_44fz_search_page(url: str) -> dict:
    provider = _get_provider()
    result = provider._fetch_page(url)
    status = result.get("status")
    if status == PublicSearchStatus.SUCCESS:
        html_content = result.get("html")
        classification = _classify_search_html(html_content) if html_content else "empty_results"
        return {
            "status": classification,
            "html": html_content if classification == "parsed" else None,
            "error": None,
        }
    return {
        "status": PublicSearchStatus.NETWORK_ERROR,
        "html": None,
        "error": result.get("error"),
    }
