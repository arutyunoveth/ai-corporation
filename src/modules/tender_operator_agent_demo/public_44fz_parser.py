from __future__ import annotations

import re
from typing import Any
from urllib.error import URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


MAX_RESPONSE_BYTES = 5 * 1024 * 1024
TIMEOUT_SECONDS = 15
USER_AGENT = "Mozilla/5.0 (compatible; ArvectumTenderAgent/0.1; read-only)"

EIS_44FZ_HOST = "zakupki.gov.ru"


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
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:
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
    title = _extract_between(entry_html, '<div class="registry-entry__header-mid__title">', "</div>")
    if title:
        title = re.sub(r"<[^>]+>", "", title).strip()
    if not title:
        title = _extract_between(entry_html, '<h2', "</h2>")
        if title:
            title = re.sub(r"<[^>]+>", "", title).strip()
    if not title:
        title_match = re.search(r'<a[^>]*class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>', entry_html)
        if title_match:
            title = title_match.group(2).strip()
    if not title:
        title_match = re.search(r'"notice__header"[^>]*>\s*<span[^>]*>([^<]+)', entry_html)
        if title_match:
            title = title_match.group(1).strip()
    if not title:
        return None

    notice_number = None
    num_link = re.search(r'class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>\s*(\d{11,25})', entry_html)
    if not num_link:
        num_link = re.search(r'href="([^"]*)"[^>]*class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*>([^<]+)', entry_html)
    if num_link:
        notice_number = num_link.group(2).strip()
    if not notice_number:
        link_match = re.search(r'href="([^"]+)"[^>]*>\s*(\d{11,25})', entry_html)
        if link_match:
            notice_number = link_match.group(2)

    reestr_number = extract_reestr_number_from_44fz_card(entry_html)

    customer_name = None
    customer_match = re.search(r'"registry-entry__body-value"[^>]*>\s*([^<]+)', entry_html)
    if customer_match:
        customer_name = customer_match.group(1).strip()
    if not customer_name:
        org_match = re.search(r'Заказчик[^:]*:\s*([^<]+)', entry_html, re.IGNORECASE)
        if org_match:
            customer_name = org_match.group(1).strip()

    initial_price = None
    price_match = re.search(r'([\d\s\xa0]+(?:руб|₽|RUB))', entry_html)
    if price_match:
        initial_price = _extract_price(price_match.group(1))

    publication_date = None
    pub_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', entry_html)
    if pub_match:
        publication_date = pub_match.group(1)

    source_url = None
    href_match = re.search(r'href="(https://[^"]*(?:zakupki\.gov\.ru)[^"]*)"', entry_html)
    if href_match:
        source_url = href_match.group(1)

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
        "deadline": None,
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
                "source_url": href if href.startswith("http") else urljoin("https://zakupki.gov.ru", href),
                "law": "44fz",
                "warnings": ["Номер извлечён из ссылки, полные данные карточки не распарсены."],
            })
    return cards
