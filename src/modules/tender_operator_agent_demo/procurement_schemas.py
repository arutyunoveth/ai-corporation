from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import Field

from src.shared.types.common import APIModel


class ProcurementSourceStatus(APIModel):
    source: str
    label: str
    enabled: bool
    configured: bool
    read_only: bool = True
    reason: str | None = None
    safe_diagnostics: dict[str, Any] = Field(default_factory=dict)


class ProcurementSearchRequest(APIModel):
    source: str = "demo_local"
    query: str = ""
    law: str | None = None
    date_from: str | None = None
    date_to: str | None = None
    customer_name: str | None = None
    customer_inn: str | None = None
    region: str | None = None
    price_from: float | None = None
    price_to: float | None = None
    max_results: int = Field(default=10, ge=1, le=50)


class ProcurementAttachment(APIModel):
    attachment_id: str
    name: str
    url: str | None = None
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    extension: str | None = None
    can_download: bool = False
    requires_manual_upload: bool = False
    warnings: list[str] = Field(default_factory=list)


class ProcurementSearchResult(APIModel):
    procurement_id: str
    notice_number: str | None = None
    registry_number: str | None = None
    title: str
    customer_name: str
    customer_inn: str | None = None
    law: str | None = None
    source: str
    source_url: str
    publication_date: str | None = None
    deadline: str | None = None
    initial_price: float | None = None
    currency: str | None = None
    status: str | None = None
    attachments_count: int = Field(default=0, ge=0)
    attachments_status: str = "unknown"
    can_download_attachments: bool = False
    requires_manual_upload: bool = True
    warnings: list[str] = Field(default_factory=list)


class ProcurementDetails(APIModel):
    procurement: ProcurementSearchResult
    attachments: list[ProcurementAttachment] = Field(default_factory=list)
    raw_source_summary: str | None = None
    warnings: list[str] = Field(default_factory=list)


class ProcurementIntakeResult(APIModel):
    run_id: str
    status: str
    run_url: str
    report_url: str | None = None
    downloaded_files_count: int = Field(default=0, ge=0)
    manual_upload_required: bool = True
    warnings: list[str] = Field(default_factory=list)


class DocsArchiveResult(APIModel):
    request_id: str
    ref_id: str | None = None
    archive_url: str | None = None
    archive_urls: list[str] = Field(default_factory=list)
    archive_name: str | None = None
    archive_size: int | None = Field(default=None, ge=0)
    status: str
    warnings: list[str] = Field(default_factory=list)
    raw_summary: str | None = None
    safe_diagnostic: dict[str, Any] = Field(default_factory=dict)


class DownloadedAttachment(APIModel):
    file_name: str
    stored_name: str
    size_bytes: int = Field(ge=0)
    content_type: str | None = None
    source_url_host: str | None = None
    source_url_path: str | None = None


class ProcurementEvent(APIModel):
    event_type: str
    timestamp: datetime
    message_ru: str
    step: str
    severity: str = Field(default="info", pattern="^(info|warning|error)$")
    metadata: dict[str, Any] = Field(default_factory=dict)
