from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from src.shared.types.common import APIModel


class ExportStatus(StrEnum):
    draft = "draft"
    blocked = "blocked"
    ready_for_review = "ready_for_review"
    approved_for_delivery = "approved_for_delivery"
    delivered_manually = "delivered_manually"
    archived = "archived"


class ExportPackage(APIModel):
    export_package_id: str = Field(min_length=1)
    partner_workspace_id: str = Field(min_length=1)
    scenario_or_tender_id: str = Field(min_length=1)
    report_refs: dict[str, str] = Field(default_factory=dict)
    included_sections: list[str] = Field(default_factory=list)
    redacted_sections: list[str] = Field(default_factory=list)
    blocked_sections: list[str] = Field(default_factory=list)
    export_status: ExportStatus = ExportStatus.draft
    review_status: str = "pending"
    export_summary: str = ""
    created_at: datetime
