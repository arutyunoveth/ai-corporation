from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class EisTenderRaw:
    external_id: str
    title: str
    customer_name: str | None = None
    customer_inn: str | None = None
    customer_kpp: str | None = None
    region: str | None = None
    law_type: str | None = None
    nmck_amount: float | None = None
    currency: str | None = None
    publication_date: datetime | None = None
    application_deadline: datetime | None = None
    auction_date: datetime | None = None
    status: str | None = None
    registry_number: str | None = None
    purchase_number: str | None = None
    eis_url: str | None = None
    description: str | None = None
    raw_payload: dict | None = None
    documents: list[EisDocumentRaw] | None = None


@dataclass
class EisDocumentRaw:
    file_name: str
    file_url: str | None = None
    source_document_id: str | None = None
    content_type: str | None = None
    size_bytes: int | None = None
    raw_meta: dict | None = None


@dataclass
class TenderUpsertData:
    tender: dict
    customer: dict | None = None
    documents: list[dict] = field(default_factory=list)


@dataclass
class SearchQuery:
    query: str
    query_type: str
    provider: str = "duckduckgo_html"


@dataclass
class SearchResult:
    rank: int
    title: str
    url: str
    normalized_url: str
    snippet: str
    display_url: str | None = None
    raw_result: dict | None = None
    url_hash: str | None = None


@dataclass
class FetchResult:
    url: str
    normalized_url: str
    url_hash: str
    status: str  # fetched / failed / blocked / timeout / non_html / too_large
    http_status: int | None = None
    content_type: str | None = None
    final_url: str | None = None
    html: str | None = None
    extracted_text: str | None = None
    extracted_title: str | None = None
    fetcher: str = "requests"
    error_message: str | None = None
