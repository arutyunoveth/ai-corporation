from __future__ import annotations

import re
from pathlib import Path

from src.tender_research.browser.fetcher import WebPageFetcher
from src.tender_research.dedupe import is_private_url, normalize_url, url_hash
from src.tender_research.schemas import FetchResult


class PlaywrightFetcher(WebPageFetcher):
    def __init__(self, headless: bool = True, save_screenshots: bool = False):
        self._headless = headless
        self._save_screenshots = save_screenshots

    def fetch(self, url: str, timeout: int = 30, max_size_mb: int = 25) -> FetchResult:
        if is_private_url(url):
            return FetchResult(
                url=url, normalized_url=normalize_url(url),
                url_hash=url_hash(url), status="blocked",
                error_message="Private URL denied",
            )
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            return FetchResult(
                url=url, normalized_url=normalize_url(url),
                url_hash=url_hash(url), status="failed",
                error_message="playwright not installed",
                fetcher="playwright",
            )
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=self._headless)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                    viewport={"width": 1280, "height": 720},
                )
                page = context.new_page()
                page.set_default_timeout(timeout * 1000)
                page.route("**/*.{png,jpg,jpeg,gif,svg,ico,woff,woff2,ttf,eot}", lambda route: route.abort())
                try:
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                    http_status = resp.status if resp else None
                    final_url = page.url
                    html = page.content()
                    title = page.title()
                    text = _extract_text_playwright(html)
                    screenshot_path = None
                    if self._save_screenshots:
                        import tempfile
                        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
                        page.screenshot(path=tmp.name)
                        screenshot_path = tmp.name
                except Exception as e:
                    return FetchResult(
                        url=url, normalized_url=normalize_url(url),
                        url_hash=url_hash(url), status="failed",
                        error_message=str(e), fetcher="playwright",
                    )
                finally:
                    browser.close()
                norm_url = normalize_url(final_url)
                return FetchResult(
                    url=url,
                    normalized_url=norm_url,
                    url_hash=url_hash(norm_url),
                    status="fetched",
                    http_status=http_status,
                    content_type="text/html",
                    final_url=final_url,
                    html=html,
                    extracted_text=text,
                    extracted_title=title,
                    fetcher="playwright",
                )
        except Exception as e:
            return FetchResult(
                url=url, normalized_url=normalize_url(url),
                url_hash=url_hash(url), status="failed",
                error_message=str(e), fetcher="playwright",
            )


def _extract_text_playwright(html: str) -> str:
    clean = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<style[^>]*>.*?</style>", "", clean, flags=re.DOTALL | re.IGNORECASE)
    clean = re.sub(r"<[^>]+>", " ", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    return clean[:500_000]
