from __future__ import annotations

from abc import ABC, abstractmethod

from src.tender_research.schemas import SearchResult


class SearchProvider(ABC):
    name: str = "abstract"

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        ...
