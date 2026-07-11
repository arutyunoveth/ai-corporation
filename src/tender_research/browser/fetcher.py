from __future__ import annotations

from abc import ABC, abstractmethod

from src.tender_research.schemas import FetchResult


class WebPageFetcher(ABC):
    @abstractmethod
    def fetch(self, url: str, timeout: int = 30, max_size_mb: int = 25) -> FetchResult:
        ...
