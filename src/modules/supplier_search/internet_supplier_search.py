from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import quote as urlquote

from src.modules.supplier_search.yandex_search_client import YandexSearchClient, YandexSearchResult


@dataclass
class FoundSupplier:
    name: str
    site: str
    snippet: str
    source_url: str
    relevance_signals: list[str] = field(default_factory=list)


@dataclass
class SupplierSearchOutcome:
    suppliers: list[FoundSupplier] = field(default_factory=list)
    query_used: str = ""
    total_found: int = 0
    error: str | None = None


_INN_PATTERN = re.compile(r"\b(\d{10,12})\b")
_PHONE_PATTERN = re.compile(r"(\+?7[ \-]?\d{3}[ \-]?\d{3}[ \-]?\d{2}[ \-]?\d{2})")
_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")


def _build_supplier_search_query(
    tender_title: str,
    notice_text: str,
    technical_spec_text: str,
) -> str:
    combined = f"{tender_title} {notice_text} {technical_spec_text}"
    signals: list[str] = []
    import re as _re
    for part in _re.split(r"[.,;!?\n]+", combined):
        part = part.strip().lower()
        for kw in ("поставк", "компьютер", "оборудован", "услуг", "работ"):
            if kw in part and len(part) > 10:
                signals.append(part[:120])
                break
    if signals:
        query = " OR ".join(signals[:3])
    else:
        query = tender_title[:200]
    query += " поставщик"
    return query


def _strip_html(html_text: str) -> str:
    clean = re.sub(r"<[^>]+>", " ", html_text)
    return re.sub(r"\s+", " ", clean).strip()


def _extract_relevance_signals(text: str) -> list[str]:
    signals: list[str] = []
    if _INN_PATTERN.search(text):
        signals.append("inn_found")
    if _PHONE_PATTERN.search(text):
        signals.append("phone_found")
    if _EMAIL_PATTERN.search(text):
        signals.append("email_found")
    for kw in ("поставщик", "производител", "дилер", "официал"):
        if kw in text.lower():
            signals.append(f"keyword_{kw}")
            break
    marketplaces = ("avito", "ozon", "wildberries", "yandex.market", "market.yandex")
    return signals


def _supplier_label(result: YandexSearchResult) -> str:
    title = _strip_html(result.title)
    domain = result.domain.lower().replace("www.", "")
    name = title.split(" — ")[0].split(" | ")[0].split(" / ")[0]
    if not name or len(name) < 5:
        name = domain.split(".")[0].capitalize()
    return name.strip()


def _is_marketplace(domain: str) -> bool:
    d = domain.lower().replace("www.", "")
    marketplaces = ("avito.ru", "ozon.ru", "wildberries.ru", "market.yandex.ru")
    return any(m in d for m in marketplaces)


def search_suppliers(
    client: YandexSearchClient,
    tender_title: str,
    notice_text: str | None = None,
    technical_spec_text: str | None = None,
    max_results: int = 10,
) -> SupplierSearchOutcome:
    query = _build_supplier_search_query(
        tender_title=tender_title,
        notice_text=notice_text or "",
        technical_spec_text=technical_spec_text or "",
    )
    response = client.search(query, max_results=max_results)
    if response.error:
        return SupplierSearchOutcome(query_used=query, error=response.error)
    suppliers: list[FoundSupplier] = []
    seen_domains: set[str] = set()
    for item in response.items:
        domain = item.domain.lower().replace("www.", "")
        if domain in seen_domains or _is_marketplace(domain):
            continue
        seen_domains.add(domain)
        name = _supplier_label(item)
        signals = _extract_relevance_signals(f"{item.title} {item.snippet}")
        suppliers.append(
            FoundSupplier(
                name=name,
                site=f"https://{domain}",
                snippet=_strip_html(item.snippet)[:300],
                source_url=item.url,
                relevance_signals=signals,
            )
        )
    return SupplierSearchOutcome(
        suppliers=suppliers,
        query_used=query,
        total_found=len(suppliers),
    )
