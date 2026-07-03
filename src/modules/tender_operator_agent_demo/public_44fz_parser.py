from __future__ import annotations

import html
import re
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import ProxyHandler, Request, build_opener


MAX_RESPONSE_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 15
USER_AGENT = "Mozilla/5.0 (compatible; ArvectumTenderAgent/0.1; read-only)"

EIS_44FZ_HOST = "zakupki.gov.ru"

PROCEDURE_CODE_LABELS = {
    "ea": "Электронный аукцион",
    "zk": "Запрос котировок",
    "ok": "Открытый конкурс",
    "eo": "Электронный конкурс",
    "ep": "Закупка у единственного поставщика",
    "zp": "Запрос предложений",
}


class Public44FzSearchStatus:
    PARSED = "parsed"
    MANUAL_OPEN_REQUIRED = "manual_open_required"
    CAPTCHA_OR_BLOCKED = "captcha_or_blocked"
    JS_HEAVY = "js_heavy"
    EMPTY_RESULTS = "empty_results"
    NETWORK_ERROR = "network_error"
    UNSUPPORTED_LAYOUT = "unsupported_layout"


def classify_public_search_response(html: str) -> str:
    if not html or not html.strip():
        return Public44FzSearchStatus.EMPTY_RESULTS

    lower = html.lower()
    captcha_markers = ["captcha", "turnstile", "recaptcha"]
    if any(marker in lower for marker in captcha_markers):
        return Public44FzSearchStatus.CAPTCHA_OR_BLOCKED
    js_heavy_markers = [
        "ваш браузер не поддерживает javascript",
        "включите javascript",
        "this site requires javascript",
    ]
    if any(marker in lower for marker in js_heavy_markers):
        return Public44FzSearchStatus.JS_HEAVY
    entry_markers = [
        "registry-entry__header-mid__number",
        "registry-entry__body-value",
        "notice__header",
        "search-results__item",
    ]
    if any(marker in lower for marker in entry_markers):
        return Public44FzSearchStatus.PARSED
    search_markers = [
        "результаты поиска",
        "найдено",
        "закупка",
        "номер извещения",
        "registry-entry",
    ]
    if any(marker in lower for marker in search_markers):
        return Public44FzSearchStatus.PARSED
    if "<html" in lower and "</html>" in lower:
        return Public44FzSearchStatus.UNSUPPORTED_LAYOUT
    return Public44FzSearchStatus.UNSUPPORTED_LAYOUT


def fetch_public_44fz_search_page(url: str) -> dict[str, Any]:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if not hostname.endswith(EIS_44FZ_HOST):
        return {
            "status": Public44FzSearchStatus.NETWORK_ERROR,
            "html": None,
            "error": f"Host {hostname} is not an allowed EIS host.",
        }
    if parsed.scheme not in {"http", "https"}:
        return {
            "status": Public44FzSearchStatus.NETWORK_ERROR,
            "html": None,
            "error": "Only http/https URLs are allowed.",
        }
    request = Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        opener = build_opener(ProxyHandler({}))
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:
            html = response.read(MAX_RESPONSE_BYTES + 1).decode("utf-8", errors="replace")
    except URLError as exc:
        return {
            "status": Public44FzSearchStatus.NETWORK_ERROR,
            "html": None,
            "error": str(exc.reason),
        }
    except Exception as exc:
        return {
            "status": Public44FzSearchStatus.NETWORK_ERROR,
            "html": None,
            "error": str(exc),
        }
    if len(html) > MAX_RESPONSE_BYTES:
        return {
            "status": Public44FzSearchStatus.NETWORK_ERROR,
            "html": None,
            "error": "Response exceeded maximum size limit.",
        }
    classification = classify_public_search_response(html)
    return {
        "status": classification,
        "html": html if classification == Public44FzSearchStatus.PARSED else None,
        "error": None,
    }


def _extract_price(text: str | None) -> float | None:
    if not text:
        return None
    cleaned = text.replace("\xa0", " ").replace(" ", "").replace(",", ".")
    match = re.search(r"(\d+(?:\.\d+)?)", cleaned)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    return None


def _extract_reestr_from_href(href: str) -> str | None:
    match = re.search(r"/(\d{3,25})", href)
    if match:
        return match.group(1)
    return None


def _extract_reestr_from_text(text: str) -> str | None:
    match = re.search(r"(\d{11,25})", text)
    if match:
        return match.group(1)
    return None


def _extract_between(html: str, prefix: str, suffix: str) -> str | None:
    start = html.find(prefix)
    if start == -1:
        return None
    start += len(prefix)
    end = html.find(suffix, start)
    if end == -1:
        return None
    return html[start:end].strip()


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"</?span[^>]*>", "", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"<br\\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned).replace("&nbsp;", " ").replace("\xa0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


def _extract_first_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{2}\.\d{2}\.\d{4}(?:\s+\d{2}:\d{2})?)", value)
    if match:
        return match.group(1).strip()
    return _strip_html(value) or None


def _extract_label_value_pairs(entry_html: str, title_class: str, value_class: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    pattern = re.compile(
        rf'<div[^>]*class="[^"]*\b{re.escape(title_class)}\b[^"]*"[^>]*>(.*?)</div>\s*'
        rf'<div[^>]*class="[^"]*\b{re.escape(value_class)}\b[^"]*"[^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(entry_html):
        label = _strip_html(match.group(1)).strip(" :")
        value = _strip_html(match.group(2))
        if label and value and label.lower() not in pairs:
            pairs[label.lower()] = value
    return pairs


def _extract_registry_body_pairs(entry_html: str) -> dict[str, str]:
    pairs: dict[str, str] = {}
    pattern = re.compile(
        r'<div[^>]*class="[^"]*\bregistry-entry__body-title\b[^"]*"[^>]*>(.*?)</div>\s*'
        r'<div[^>]*class="[^"]*\bregistry-entry__body-(?:value|href)\b[^"]*"[^>]*>(.*?)</div>',
        re.IGNORECASE | re.DOTALL,
    )
    for match in pattern.finditer(entry_html):
        label = _strip_html(match.group(1)).strip(" :")
        value = _strip_html(match.group(2))
        if label and value and label.lower() not in pairs:
            pairs[label.lower()] = value
    return pairs


def _first_matching_value(pairs: dict[str, str], labels: tuple[str, ...]) -> str | None:
    for label in labels:
        value = pairs.get(label.lower())
        if value:
            return value
    return None


def _extract_procedure_type(source_url: str | None) -> str | None:
    if not source_url:
        return None
    match = re.search(r"/notice/([a-z]{2})\d+/view", source_url, re.IGNORECASE)
    if not match:
        return None
    return PROCEDURE_CODE_LABELS.get(match.group(1).lower())


def extract_reestr_number_from_44fz_card(html_fragment: str) -> str | None:
    reestr = _extract_reestr_from_text(html_fragment)
    if reestr:
        return reestr
    href_match = re.search(r'href="([^"]*/(\d{11,25})[^"]*)"', html_fragment)
    if href_match:
        return href_match.group(2)
    return _extract_reestr_from_href(html_fragment)


def parse_44fz_search_results(html: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    entries = _split_registry_entries(html)
    for entry_html in entries:
        card = _parse_single_entry(entry_html, html)
        if card:
            cards.append(card)
    if not cards:
        cards = _fallback_extract_by_number_patterns(html)
    return cards


def _split_registry_entries(html: str) -> list[str]:
    patterns = [
        r'<div[^>]*class="[^"]*\bregistry-entry\b[^"]*"[^>]*>',
        r'<div[^>]*class="[^"]*\bnotice__item\b[^"]*"[^>]*>',
        r'<div[^>]*class="[^"]*\bsearch-results__item\b[^"]*"[^>]*>',
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, html, re.IGNORECASE))
        if len(matches) >= 1:
            fragments: list[str] = []
            for i, match in enumerate(matches):
                start = match.start()
                if i + 1 < len(matches):
                    end = matches[i + 1].start()
                else:
                    end = len(html)
                fragments.append(html[start:end])
            return fragments
    return []


def _parse_single_entry(entry_html: str, full_html: str) -> dict[str, Any] | None:
    pairs: dict[str, str] = _extract_registry_body_pairs(entry_html)
    for title_class, value_class in (
        ("data-block__title", "data-block__value"),
        ("price-block__title", "price-block__value"),
    ):
        pairs.update(_extract_label_value_pairs(entry_html, title_class, value_class))

    title = _first_matching_value(
        pairs,
        (
            "объект закупки",
            "наименование объекта закупки",
            "предмет контракта",
            "предмет договора",
        ),
    )
    if not title:
        title = _extract_between(entry_html, '<div class="registry-entry__header-mid__title">', "</div>")
    if title:
        title = _strip_html(title)
    if not title:
        title = _extract_between(entry_html, '<h2', "</h2>")
        if title:
            title = _strip_html(title)
    if not title:
        title_match = re.search(r'<a[^>]*class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', entry_html)
        if title_match:
            title = _strip_html(title_match.group(2))
    if not title:
        title_match = re.search(r'"notice__header"[^>]*>\s*<span[^>]*>([^<]+)', entry_html)
        if title_match:
            title = _strip_html(title_match.group(1))
    if not title:
        return None

    notice_number = None
    num_link = re.search(r'class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>.*?(\d{11,25})', entry_html, re.DOTALL)
    if not num_link:
        num_link = re.search(r'href="([^"]*)"[^>]*class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*>.*?(\d{11,25})', entry_html, re.DOTALL)
    if num_link:
        notice_number = num_link.group(2).strip()
    if not notice_number:
        link_match = re.search(r'href="([^"]+)"[^>]*>\s*(\d{11,25})', entry_html)
        if link_match:
            notice_number = link_match.group(2)

    reestr_number = extract_reestr_number_from_44fz_card(entry_html)

    customer_name = _first_matching_value(
        pairs,
        (
            "заказчик",
            "организация, осуществляющая размещение",
            "организация",
        ),
    )
    if not customer_name:
        org_match = re.search(r'Заказчик[^:]*:\s*([^<]+)', entry_html, re.IGNORECASE)
        if org_match:
            customer_name = _strip_html(org_match.group(1))

    price_value = _first_matching_value(
        pairs,
        (
            "начальная цена",
            "начальная (максимальная) цена контракта",
            "максимальное значение цены контракта",
            "цена контракта",
        ),
    )
    initial_price = _extract_price(price_value)
    if initial_price is None:
        price_match = re.search(r'([\d\s\xa0,.]+(?:руб|₽|RUB))', entry_html, re.IGNORECASE)
    else:
        price_match = None
    if price_match:
        initial_price = _extract_price(price_match.group(1))

    publication_date = _extract_first_date(
        _first_matching_value(
            pairs,
            (
                "размещено",
                "дата размещения",
                "опубликовано",
            ),
        )
    )
    if not publication_date:
        pub_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', entry_html)
        if pub_match:
            publication_date = pub_match.group(1)

    deadline = _extract_first_date(
        _first_matching_value(
            pairs,
            (
                "окончание подачи заявок",
                "дата окончания срока подачи заявок",
                "срок подачи заявок",
            ),
        )
    )

    source_url = None
    href_match = re.search(r'href="(https://[^"]*(?:zakupki\.gov\.ru)[^"]*)"', entry_html)
    if href_match:
        source_url = href_match.group(1)
    if not source_url:
        href_match = re.search(r'href="([^"]*(?:view|common-info)[^"]*)"', entry_html)
        if href_match:
            source_url = urljoin("https://zakupki.gov.ru", href_match.group(1))

    procedure_status = _strip_html(
        _extract_between(entry_html, '<div class="registry-entry__header-mid__title text-normal">', "</div>")
        or _extract_between(entry_html, '<div class="registry-entry__header-mid__title">', "</div>")
    )
    procedure_type = _extract_procedure_type(source_url)

    warnings: list[str] = []
    if not notice_number and not reestr_number:
        warnings.append("Не удалось извлечь номер закупки из выдачи ЕИС.")

    return {
        "title": title,
        "notice_number": notice_number,
        "reestr_number": reestr_number or notice_number,
        "customer_name": customer_name,
        "initial_price": initial_price,
        "publication_date": publication_date,
        "deadline": deadline,
        "procedure_type": procedure_type,
        "status": procedure_status or None,
        "source_url": source_url,
        "law": "44fz",
        "warnings": warnings,
    }


def _fallback_extract_by_number_patterns(html: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    number_pattern = re.compile(r"(\d{11,25})")
    links = re.finditer(r'<a[^>]*href="([^"]*)"[^>]*>', html)
    seen_numbers: set[str] = set()
    for link in links:
        href = link.group(1)
        match = number_pattern.search(href)
        if match and match.group(1) not in seen_numbers:
            seen_numbers.add(match.group(1))
            cards.append({
                "title": f"Закупка № {match.group(1)}",
                "notice_number": match.group(1),
                "reestr_number": match.group(1),
                "customer_name": None,
                "initial_price": None,
                "publication_date": None,
                "deadline": None,
                "procedure_type": _extract_procedure_type(href if href.startswith("http") else urljoin("https://zakupki.gov.ru", href)),
                "status": None,
                "source_url": href if href.startswith("http") else urljoin("https://zakupki.gov.ru", href),
                "law": "44fz",
                "warnings": ["Номер извлечён из ссылки, полные данные карточки не распарсены."],
            })
    return cards
