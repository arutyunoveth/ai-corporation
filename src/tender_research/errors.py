from __future__ import annotations


class TenderResearchError(Exception):
    pass


class EisLoaderError(TenderResearchError):
    pass


class DocumentStoreError(TenderResearchError):
    pass


class SearchProviderError(TenderResearchError):
    pass


class FetchError(TenderResearchError):
    pass


class RateLimitError(TenderResearchError):
    pass
