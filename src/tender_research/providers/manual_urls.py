from __future__ import annotations

from src.tender_research.dedupe import normalize_url, url_hash
from src.tender_research.schemas import SearchResult
from src.tender_research.search_provider import SearchProvider


class ManualUrlsSearchProvider(SearchProvider):
    name: str = "manual"

    def __init__(self, urls: list[dict[str, str]] | None = None):
        self._urls = urls or []

    def add(self, title: str, url: str, snippet: str = "") -> None:
        self._urls.append({"title": title, "url": url, "snippet": snippet})

    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        results = []
        for i, entry in enumerate(self._urls):
            normalized = normalize_url(entry["url"])
            results.append(
                SearchResult(
                    rank=i + 1,
                    title=entry["title"],
                    url=entry["url"],
                    normalized_url=normalized,
                    snippet=entry.get("snippet", ""),
                    url_hash=url_hash(normalized),
                )
            )
        return results[:limit]
