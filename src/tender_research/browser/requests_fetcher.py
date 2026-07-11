from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser
from urllib.parse import urlparse

from src.tender_research.browser.fetcher import WebPageFetcher
from src.tender_research.dedupe import is_private_url, normalize_url, url_hash
from src.tender_research.schemas import FetchResult


class RequestsFetcher(WebPageFetcher):
    def fetch(self, url: str, timeout: int = 30, max_size_mb: int = 25) -> FetchResult:
        if is_private_url(url):
            return FetchResult(
                url=url,
                normalized_url=normalize_url(url),
                url_hash=url_hash(url),
                status="blocked",
                error_message="Private URL denied",
            )
        max_bytes = max_size_mb * 1024 * 1024
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                content_type = resp.headers.get("Content-Type", "") or ""
                final_url = resp.url or url
                if "text/html" not in content_type and "text/plain" not in content_type:
                    body = resp.read(max_bytes + 1)
                    if len(body) > max_bytes:
                        return FetchResult(
                            url=url, normalized_url=normalize_url(url),
                            url_hash=url_hash(url), status="too_large",
                            http_status=resp.status, content_type=content_type,
                            final_url=final_url, fetcher="requests",
                        )
                    return FetchResult(
                        url=url, normalized_url=normalize_url(url),
                        url_hash=url_hash(url), status="non_html",
                        http_status=resp.status, content_type=content_type,
                        final_url=final_url, fetcher="requests",
                    )
                body = resp.read(max_bytes + 1)
                if len(body) > max_bytes:
                    return FetchResult(
                        url=url, normalized_url=normalize_url(url),
                        url_hash=url_hash(url), status="too_large",
                        http_status=resp.status, content_type=content_type,
                        final_url=final_url, fetcher="requests",
                    )
                encoding = resp.headers.get_content_charset() or "utf-8"
                html = body.decode(encoding, errors="replace")
                title = _extract_title(html)
                text = _extract_text(html)
                norm_url = normalize_url(final_url)
                return FetchResult(
                    url=url,
                    normalized_url=norm_url,
                    url_hash=url_hash(norm_url),
                    status="fetched",
                    http_status=resp.status,
                    content_type=content_type,
                    final_url=final_url,
                    html=html,
                    extracted_text=text,
                    extracted_title=title,
                    fetcher="requests",
                )
        except urllib.error.HTTPError as e:
            return FetchResult(
                url=url, normalized_url=normalize_url(url),
                url_hash=url_hash(url), status="failed",
                http_status=e.code, error_message=str(e), fetcher="requests",
            )
        except urllib.error.URLError as e:
            return FetchResult(
                url=url, normalized_url=normalize_url(url),
                url_hash=url_hash(url), status="timeout" if "timeout" in str(e).lower() else "failed",
                error_message=str(e), fetcher="requests",
            )
        except Exception as e:
            return FetchResult(
                url=url, normalized_url=normalize_url(url),
                url_hash=url_hash(url), status="failed",
                error_message=str(e), fetcher="requests",
            )


def _extract_title(html: str) -> str:
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    return m.group(1).strip() if m else ""


def _extract_text(html: str) -> str:
    clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:500_000]
