from __future__ import annotations

import html
import logging
import os
import re
import ssl
import time
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlparse
from urllib.request import HTTPSHandler, ProxyHandler, Request, build_opener

logger = logging.getLogger(__name__)

EIS_44FZ_HOST = "zakupki.gov.ru"
EIS_44FZ_SEARCH_PATH = "/epz/order/extendedsearch/results.html"
MAX_RESPONSE_BYTES = 5 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_PAGE_SIZE = 30
MAX_PAGE_SIZE = 100
USER_AGENT = "Mozilla/5.0 (compatible; ArvectumTenderAgent/0.1; read-only)"

LAW_FLAGS = {
    "44fz": "fz44",
    "223fz": "fz223",
    "capital_repair": "ppRf615",
}


class PublicSearchStatus:
    SUCCESS = "success"
    BLOCKED = "blocked"
    TIMEOUT = "timeout"
    BAD_GATEWAY = "bad_gateway"
    CAPTCHA = "captcha"
    PARSE_ERROR = "parse_error"
    EMPTY = "empty"
    NETWORK_ERROR = "network_error"


@dataclass
class PublicTenderSearchItem:
    registry_number: str | None = None
    purchase_number: str | None = None
    title: str | None = None
    customer_name: str | None = None
    customer_inn: str | None = None
    publication_date: str | None = None
    application_deadline: str | None = None
    nmck_amount: float | None = None
    source_url: str | None = None
    raw: dict[str, Any] | None = None


@dataclass
class PublicTenderSearchPage:
    items: list[PublicTenderSearchItem] = field(default_factory=list)
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE
    has_next: bool | None = None
    total: int | None = None
    source_url: str | None = None
    raw_html_path: str | None = None
    status: str = PublicSearchStatus.SUCCESS
    error: str | None = None


DEFAULT_NO_PROXY_DOMAINS = (
    "zakupki.gov.ru",
    ".zakupki.gov.ru",
    "int.zakupki.gov.ru",
    "int44.zakupki.gov.ru",
)
PUBLIC_SEARCH_NO_PROXY_DOMAINS = DEFAULT_NO_PROXY_DOMAINS


def _hostname_matches_no_proxy(hostname: str, no_proxy_domains: tuple[str, ...]) -> bool:
    hostname = hostname.lower().strip()
    for domain in no_proxy_domains:
        domain = domain.lower().strip()
        if not domain:
            continue
        if domain.startswith("."):
            if hostname.endswith(domain) or hostname == domain.lstrip("."):
                return True
        elif hostname == domain or hostname.endswith(f".{domain}"):
            return True
    return False


def _resolve_no_proxy_domains(config_domains: str | None, env_domains: str | None = None) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    default = ",".join(PUBLIC_SEARCH_NO_PROXY_DOMAINS)
    sources = [config_domains or default, env_domains or "", os.environ.get("NO_PROXY", ""), os.environ.get("no_proxy", "")]
    for raw in sources:
        for part in raw.split(","):
            part = part.strip()
            if part and part not in seen:
                seen.add(part)
                result.append(part)
    return tuple(result) if result else DEFAULT_NO_PROXY_DOMAINS


class Public44FzSearchProvider:
    def __init__(
        self,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        delay_seconds: float = 0.0,
        bypass_proxy: bool = True,
        no_proxy_domains: str | None = None,
    ):
        self._timeout = timeout_seconds
        self._delay = delay_seconds
        self._bypass_proxy = bypass_proxy
        self._no_proxy_domains = _resolve_no_proxy_domains(no_proxy_domains)

    def search(
        self,
        query: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        law_type: str = "44fz",
        status_filter: str | None = None,
    ) -> PublicTenderSearchPage:
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE
        url = self._build_url(
            query=query,
            date_from=date_from,
            date_to=date_to,
            page=page,
            page_size=page_size,
            law_type=law_type,
        )
        logger.info("Fetching EIS public search: %s", url)

        fetch_result = self._fetch_page(url)
        status = fetch_result.get("status")
        if status != PublicSearchStatus.SUCCESS or not fetch_result.get("html"):
            return PublicTenderSearchPage(
                page=page,
                page_size=page_size,
                source_url=url,
                status=status or PublicSearchStatus.NETWORK_ERROR,
                error=fetch_result.get("error"),
            )

        cards = parse_44fz_search_results(fetch_result["html"])
        items = [self._card_to_item(c) for c in cards]
        has_next = len(cards) >= page_size

        return PublicTenderSearchPage(
            items=items,
            page=page,
            page_size=page_size,
            has_next=has_next,
            source_url=url,
            status=PublicSearchStatus.SUCCESS if items else PublicSearchStatus.EMPTY,
        )

    def search_pages(
        self,
        query: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        max_pages: int = 3,
        page_size: int = DEFAULT_PAGE_SIZE,
        law_type: str = "44fz",
    ) -> list[PublicTenderSearchPage]:
        pages: list[PublicTenderSearchPage] = []
        for page_num in range(1, max_pages + 1):
            if self._delay > 0 and page_num > 1:
                time.sleep(self._delay)
            result = self.search(
                query=query,
                date_from=date_from,
                date_to=date_to,
                page=page_num,
                page_size=page_size,
                law_type=law_type,
            )
            pages.append(result)
            if result.status != PublicSearchStatus.SUCCESS:
                break
            if not result.has_next:
                break
        return pages

    def _build_url(
        self,
        query: str | None = None,
        date_from: date | None = None,
        date_to: date | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        law_type: str = "44fz",
    ) -> str:
        normalized_law = _normalize_law(law_type)
        flag = LAW_FLAGS.get(normalized_law, "fz44")
        if date_from is None:
            date_from = date.today() - timedelta(days=3)
        if date_to is None:
            date_to = date.today()
        params = {
            "searchString": query or "",
            "morphology": "on",
            "sortDirection": "false",
            flag: "on",
            "publishDateFrom": date_from.strftime("%d.%m.%Y"),
            "publishDateTo": date_to.strftime("%d.%m.%Y"),
            "pageNumber": str(page),
            "recordsPerPage": str(min(max(page_size, 1), MAX_PAGE_SIZE)),
        }
        return f"https://{EIS_44FZ_HOST}{EIS_44FZ_SEARCH_PATH}?{urlencode(params)}"

    def _fetch_page(self, url: str) -> dict[str, Any]:
        parsed = urlparse(url)
        hostname = (parsed.hostname or "").lower()
        if not hostname.endswith(EIS_44FZ_HOST):
            return {"status": PublicSearchStatus.NETWORK_ERROR, "html": None, "error": f"Host {hostname} is not allowed"}
        if parsed.scheme not in {"http", "https"}:
            return {"status": PublicSearchStatus.NETWORK_ERROR, "html": None, "error": "Only http/https URLs"}

        request = Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
        ssl_ctx = ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = ssl.CERT_NONE

        should_bypass = self._bypass_proxy and _hostname_matches_no_proxy(hostname, self._no_proxy_domains)
        if should_bypass:
            opener = build_opener(HTTPSHandler(context=ssl_ctx), ProxyHandler({}))
        else:
            opener = build_opener(HTTPSHandler(context=ssl_ctx))

        try:
            with opener.open(request, timeout=self._timeout) as response:
                raw = response.read(MAX_RESPONSE_BYTES + 1)
                if len(raw) > MAX_RESPONSE_BYTES:
                    return {"status": PublicSearchStatus.NETWORK_ERROR, "html": None, "error": "Response too large"}
                html_content = raw.decode("utf-8", errors="replace")
        except HTTPError as exc:
            code = exc.code
            if code in (502, 503):
                return {"status": PublicSearchStatus.BAD_GATEWAY, "html": None, "error": f"HTTP {code}"}
            if code == 403:
                return {"status": PublicSearchStatus.BLOCKED, "html": None, "error": f"HTTP {code} Forbidden"}
            return {"status": PublicSearchStatus.NETWORK_ERROR, "html": None, "error": f"HTTP {code}"}
        except URLError as exc:
            reason = str(exc.reason) if hasattr(exc, "reason") else str(exc)
            reason_lower = reason.lower()
            if "timed out" in reason_lower or "timeout" in reason_lower:
                return {"status": PublicSearchStatus.TIMEOUT, "html": None, "error": reason}
            if "connection reset" in reason_lower:
                return {"status": PublicSearchStatus.BLOCKED, "html": None, "error": reason}
            return {"status": PublicSearchStatus.NETWORK_ERROR, "html": None, "error": reason}
        except Exception as exc:
            return {"status": PublicSearchStatus.NETWORK_ERROR, "html": None, "error": str(exc)}

        classification = _classify_search_html(html_content)
        if classification != "parsed":
            if classification == "captcha_or_blocked":
                return {"status": PublicSearchStatus.BLOCKED, "html": None, "error": "Captcha or blocking detected"}
            if classification == "empty_results":
                return {"status": PublicSearchStatus.SUCCESS, "html": html_content, "error": None}
            if classification == "unsupported_layout":
                return {"status": PublicSearchStatus.PARSE_ERROR, "html": None, "error": f"Unsupported layout: {classification}"}
            return {"status": PublicSearchStatus.PARSE_ERROR, "html": None, "error": f"Unclassified: {classification}"}

        return {"status": PublicSearchStatus.SUCCESS, "html": html_content, "error": None}

    @staticmethod
    def _card_to_item(card: dict[str, Any]) -> PublicTenderSearchItem:
        nmck = None
        raw_price = card.get("initial_price")
        if raw_price is not None:
            try:
                nmck = float(raw_price)
            except (ValueError, TypeError):
                nmck = None
        return PublicTenderSearchItem(
            registry_number=card.get("reestr_number"),
            purchase_number=card.get("notice_number"),
            title=card.get("title"),
            customer_name=card.get("customer_name"),
            publication_date=card.get("publication_date"),
            application_deadline=card.get("deadline"),
            nmck_amount=nmck,
            source_url=card.get("source_url"),
            raw=card,
        )

    @staticmethod
    def extract_registry_numbers(pages: list[PublicTenderSearchPage]) -> list[str]:
        seen: set[str] = set()
        numbers: list[str] = []
        for page_obj in pages:
            for item in page_obj.items:
                if item.registry_number and item.registry_number not in seen:
                    seen.add(item.registry_number)
                    numbers.append(item.registry_number)
        return numbers


def _normalize_law(law: str | None) -> str:
    normalized = (law or "44fz").strip().lower().replace("-", "").replace("_", "")
    if normalized in {"44фз", "44fz", "44"}:
        return "44fz"
    if normalized in {"223фз", "223fz", "223"}:
        return "223fz"
    if normalized in {"капремонт", "капрем", "capitalrepair", "615", "pp615", "pprf615", "615pp"}:
        return "capital_repair"
    return "44fz"


def _classify_search_html(html_content: str) -> str:
    if not html_content or not html_content.strip():
        return "empty_results"
    lower = html_content.lower()
    captcha_markers = ["captcha", "turnstile", "recaptcha"]
    if any(marker in lower for marker in captcha_markers):
        return "captcha_or_blocked"
    js_heavy_markers = [
        "your browser does not support javascript",
        "ваш браузер не поддерживает javascript",
        "включите javascript",
        "this site requires javascript",
    ]
    if any(marker in lower for marker in js_heavy_markers):
        return "captcha_or_blocked"
    entry_markers = [
        "registry-entry__header-mid__number",
        "registry-entry__body-value",
        "notice__header",
        "search-results__item",
    ]
    if any(marker in lower for marker in entry_markers):
        return "parsed"
    search_markers = [
        "результаты поиска",
        "найдено",
        "закупка",
        "номер извещения",
        "registry-entry",
    ]
    if any(marker in lower for marker in search_markers):
        return "parsed"
    if "<html" in lower and "</html>" in lower:
        return "unsupported_layout"
    return "unsupported_layout"


# ── HTML parsing (from public_44fz_parser.py) ──

PROCEDURE_CODE_LABELS = {
    "ea": "Электронный аукцион",
    "zk": "Запрос котировок",
    "ok": "Открытый конкурс",
    "eo": "Электронный конкурс",
    "ep": "Закупка у единственного поставщика",
    "zp": "Запрос предложений",
}


def parse_44fz_search_results(html_str: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    entries = _split_registry_entries(html_str)
    for entry_html in entries:
        card = _parse_single_entry(entry_html, html_str)
        if card:
            cards.append(card)
    if not cards:
        cards = _fallback_extract_by_number_patterns(html_str)
    return cards


def _split_registry_entries(html_str: str) -> list[str]:
    patterns = [
        r'<div[^>]*class="[^"]*\bregistry-entry\b[^"]*"[^>]*>',
        r'<div[^>]*class="[^"]*\bnotice__item\b[^"]*"[^>]*>',
        r'<div[^>]*class="[^"]*\bsearch-results__item\b[^"]*"[^>]*>',
    ]
    for pattern in patterns:
        matches = list(re.finditer(pattern, html_str, re.IGNORECASE))
        if len(matches) >= 1:
            fragments: list[str] = []
            for i, match in enumerate(matches):
                start = match.start()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(html_str)
                fragments.append(html_str[start:end])
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
        title = _extract_between(entry_html, "<h2", "</h2>")
        if title:
            title = _strip_html(title)
    if not title:
        title_match = re.search(
            r'<a[^>]*class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*href="([^"]*)"[^>]*>([^<]+)</a>',
            entry_html,
        )
        if title_match:
            title = _strip_html(title_match.group(2))
    if not title:
        title_match = re.search(r'"notice__header"[^>]*>\s*<span[^>]*>([^<]+)', entry_html)
        if title_match:
            title = _strip_html(title_match.group(1))
    if not title:
        return None

    notice_number = None
    num_link = re.search(
        r'class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*>\s*<a[^>]*href="([^"]*)"[^>]*>.*?(\d{11,25})',
        entry_html,
        re.DOTALL,
    )
    if not num_link:
        num_link = re.search(
            r'href="([^"]*)"[^>]*class="[^"]*registry-entry__header-mid__number[^"]*"[^>]*>.*?(\d{11,25})',
            entry_html,
            re.DOTALL,
        )
    if num_link:
        notice_number = num_link.group(2).strip()
    if not notice_number:
        link_match = re.search(r'href="([^"]+)"[^>]*>\s*(\d{11,25})', entry_html)
        if link_match:
            notice_number = link_match.group(2)

    reestr_number = _extract_reestr_from_card(entry_html)

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
        _first_matching_value(pairs, ("размещено", "дата размещения", "опубликовано"))
    )
    if not publication_date:
        pub_match = re.search(r"(\d{2}\.\d{2}\.\d{4})", entry_html)
        if pub_match:
            publication_date = pub_match.group(1)

    deadline = _extract_first_date(
        _first_matching_value(pairs, ("окончание подачи заявок", "дата окончания срока подачи заявок", "срок подачи заявок"))
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
    }


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


def _first_matching_value(pairs: dict[str, str], labels: tuple[str, ...]) -> str | None:
    for label in labels:
        value = pairs.get(label.lower())
        if value:
            return value
    return None


def _extract_between(html_str: str, prefix: str, suffix: str) -> str | None:
    start = html_str.find(prefix)
    if start == -1:
        return None
    start += len(prefix)
    end = html_str.find(suffix, start)
    if end == -1:
        return None
    return html_str[start:end].strip()


def _strip_html(value: str | None) -> str:
    if not value:
        return ""
    cleaned = re.sub(r"</?span[^>]*>", "", value, flags=re.IGNORECASE)
    cleaned = re.sub(r"<br\\s*/?>", "\n", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned).replace("&nbsp;", " ").replace("\xa0", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.strip()


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


def _extract_reestr_from_card(html_str: str) -> str | None:
    reestr = _extract_reestr_from_text(html_str)
    if reestr:
        return reestr
    href_match = re.search(r'href="([^"]*/(\d{11,25})[^"]*)"', html_str)
    if href_match:
        return href_match.group(2)
    href_match2 = re.search(r"/(\d{3,25})", html_str)
    if href_match2:
        return href_match2.group(1)
    return None


def _extract_reestr_from_text(text: str) -> str | None:
    match = re.search(r"(\d{11,25})", text)
    if match:
        return match.group(1)
    return None


def _extract_first_date(value: str | None) -> str | None:
    if not value:
        return None
    match = re.search(r"(\d{2}\.\d{2}\.\d{4}(?:\s+\d{2}:\d{2})?)", value)
    if match:
        return match.group(1).strip()
    return _strip_html(value) or None


def _extract_procedure_type(source_url: str | None) -> str | None:
    if not source_url:
        return None
    match = re.search(r"/notice/([a-z]{2})\d+/view", source_url, re.IGNORECASE)
    if not match:
        return None
    return PROCEDURE_CODE_LABELS.get(match.group(1).lower())


def _fallback_extract_by_number_patterns(html_str: str) -> list[dict[str, Any]]:
    cards: list[dict[str, Any]] = []
    number_pattern = re.compile(r"(\d{11,25})")
    links = re.finditer(r'<a[^>]*href="([^"]*)"[^>]*>', html_str)
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
                "procedure_type": _extract_procedure_type(
                    href if href.startswith("http") else urljoin("https://zakupki.gov.ru", href)
                ),
                "status": None,
                "source_url": href if href.startswith("http") else urljoin("https://zakupki.gov.ru", href),
                "law": "44fz",
            })
    return cards
