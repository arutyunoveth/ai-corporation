from __future__ import annotations

import re as _re
from typing import Any

from src.tender_research.schemas import SearchQuery

_STOP_WORDS = frozenset({
    "закупка", "поставка", "оказание", "выполнение", "услуг", "услуги", "услугу",
    "для нужд", "нужд", "нужды", "государственный", "муниципальный",
    "федеральный", "региональный", "местный", "бюджетный",
    "внебюджетный", "учреждение", "предприятие", "организация",
    "общество", "ограниченной", "ответственностью", "акционерное",
    "закрытое", "открытое", "публичное",
})

_MAX_QUERY_LENGTH = 240
_MAX_QUERIES_DEFAULT = 8


def build_search_queries(
    tender_title: str,
    customer_name: str | None = None,
    customer_inn: str | None = None,
    registry_number: str | None = None,
    purchase_number: str | None = None,
    extracted_keywords: list[str] | None = None,
    okpd: str | None = None,
    max_queries: int = _MAX_QUERIES_DEFAULT,
) -> list[SearchQuery]:
    queries: list[SearchQuery] = []
    seen: set[str] = set()

    title_clean = _clean_title(tender_title)
    keywords = _extract_keywords(title_clean)
    short_item = " ".join(keywords[:4]) if keywords else title_clean[:120]

    def add(q: str, qtype: str) -> None:
        q = _normalize_query(q)
        if not q or len(q) > _MAX_QUERY_LENGTH:
            return
        if q in seen:
            return
        seen.add(q)
        queries.append(SearchQuery(query=q, query_type=qtype))

    # 1. Exact title queries (use cleaned title to remove stop words)
    title_clean_for_query = _clean_title(tender_title)
    if title_clean_for_query:
        add(title_clean_for_query, "exact_title")
        add(f'{title_clean_for_query} техническое задание', "exact_title")

    # 2. Customer queries
    if customer_inn:
        add(f'{customer_inn} заказчик закупки', "customer")
    if customer_name:
        add(f'{customer_name} закупки', "customer")

    # 3. Item/supplier queries
    if short_item:
        add(f'{short_item} поставщик', "supplier")
        add(f'{short_item} официальный дилер', "supplier")
        add(f'{short_item} производитель', "manufacturer")
        add(f'{short_item} каталог pdf', "catalog")
        add(f'{short_item} технические характеристики', "keywords")

    # 4. Registry/purchase number (high priority)
    if registry_number:
        add(f'{registry_number}', "exact_title")
    if purchase_number and purchase_number != registry_number:
        add(f'{purchase_number}', "exact_title")

    # 5. Price queries
    if short_item:
        add(f'{short_item} цена', "price")
        add(f'{short_item} прайс-лист', "price")
        add(f'{short_item} коммерческое предложение', "price")

    # 6. OKPD
    if okpd:
        add(f'{okpd} поставщик', "okpd")
        add(f'{okpd} цена', "okpd")

    return queries[:max_queries]


def _stem_match(word: str, stop_word: str) -> bool:
    if word == stop_word:
        return True
    min_len = min(len(word), len(stop_word))
    if min_len < 4:
        return False
    common = 0
    for a, b in zip(word, stop_word):
        if a != b:
            break
        common += 1
    return common >= min_len - 2

def _clean_title(title: str) -> str:
    clean = title.lower()
    words = clean.split()
    filtered = []
    for word in words:
        is_stop = False
        for sw in _STOP_WORDS:
            if _stem_match(word, sw):
                is_stop = True
                break
        if not is_stop:
            filtered.append(word)
    return " ".join(filtered)


def _extract_keywords(text: str) -> list[str]:
    tokens = _re.findall(r"[а-яёa-z0-9]{4,}", text.lower())
    seen = set()
    result = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result


def _normalize_query(q: str) -> str:
    q = q.replace("«", "").replace("»", "").replace('"', "").replace("'", "")
    q = _re.sub(r"\s+", " ", q).strip()
    return q[: _MAX_QUERY_LENGTH]
