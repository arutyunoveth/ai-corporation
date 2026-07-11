from __future__ import annotations

import re
import urllib.parse
import urllib.request
from html.parser import HTMLParser

from src.tender_research.dedupe import normalize_url, url_hash
from src.tender_research.schemas import SearchResult
from src.tender_research.search_provider import SearchProvider


class DuckDuckGoHtmlSearchProvider(SearchProvider):
    name: str = "duckduckgo_html"

    def __init__(self, timeout: int = 20):
        self._timeout = timeout

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        params = urllib.parse.urlencode({"q": query})
        url = f"https://html.duckduckgo.com/html/?{params}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                html = resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            return []
        return _parse_ddg_html(html, limit)


def _parse_ddg_html(html: str, limit: int) -> list[SearchResult]:
    parser = _DdgHtmlParser()
    parser.feed(html)
    results = []
    seen_hashes: set[str] = set()
    for item in parser.results:
        normalized = normalize_url(item["url"])
        h = url_hash(normalized)
        if h in seen_hashes:
            continue
        seen_hashes.add(h)
        results.append(
            SearchResult(
                rank=len(results) + 1,
                title=item["title"],
                url=item["url"],
                normalized_url=normalized,
                snippet=item["snippet"],
                url_hash=h,
            )
        )
        if len(results) >= limit:
            break
    return results


class _DdgHtmlParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.results: list[dict[str, str]] = []
        self._in_result = False
        self._in_title = False
        self._in_snippet = False
        self._in_link = False
        self._current: dict[str, str] = {}
        self._skip_depth = 0
        self._last_a_href = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attrs_dict = dict(attrs)
        cls = attrs_dict.get("class", "")
        if tag == "div" and "result" in cls and "results_links" not in cls and "result__body" not in cls:
            if self._in_result:
                self._skip_depth += 1
            else:
                self._in_result = True
                self._current = {}
        elif self._in_result and tag == "a" and "result__a" in cls:
            self._in_title = True
            href = attrs_dict.get("href", "")
            self._last_a_href = _extract_ddg_url(href) or href
        elif self._in_result and tag == "a" and "result__snippet" in cls:
            self._in_snippet = True
        elif self._in_result and tag == "a":
            href = attrs_dict.get("href", "")
            if "uddg=" in href or "//duckduckgo.com/l/" in href:
                self._last_a_href = _extract_ddg_url(href) or href

    def handle_endtag(self, tag: str) -> None:
        if self._in_result and tag == "div":
            if self._skip_depth > 0:
                self._skip_depth -= 1
            else:
                self._finish_current()

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self._current["title"] = (self._current.get("title", "") + data).strip()
        elif self._in_snippet:
            self._current["snippet"] = (self._current.get("snippet", "") + data).strip()

    def handle_entityref(self, name: str) -> None:
        if self._in_title:
            self._current["title"] = self._current.get("title", "") + f"&{name};"
        elif self._in_snippet:
            self._current["snippet"] = self._current.get("snippet", "") + f"&{name};"

    def _finish_current(self) -> None:
        if self._current.get("title") and self._last_a_href:
            self._current["url"] = self._last_a_href
            self.results.append(self._current)
        self._in_result = False
        self._in_title = False
        self._in_snippet = False
        self._current = {}
        self._last_a_href = ""


_DDG_URL_RE = re.compile(r"uddg=([^&]+)")


def _extract_ddg_url(href: str) -> str | None:
    m = _DDG_URL_RE.search(href)
    if m:
        return urllib.parse.unquote(m.group(1))
    return None
