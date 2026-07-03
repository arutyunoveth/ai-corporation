from __future__ import annotations

from datetime import datetime
from typing import Literal

from src.shared.types.common import APIModel


ReviewSeverity = Literal["info", "warning", "blocking"]
ReviewOverallStatus = Literal["ready_for_review", "blocked", "needs_operator_input"]


class HumanReviewItem(APIModel):
    item_id: str
    section: str
    severity: ReviewSeverity
    title: str
    description: str
    source_file: str
    source_field: str
    suggested_action: str
    requires_operator_input: bool
    resolved: bool = False


class HumanReviewPack(APIModel):
    review_pack_id: str
    tender_label: str
    operator_id: str
    generated_at: datetime
    overall_status: ReviewOverallStatus
    blocking_count: int
    warning_count: int
    info_count: int
    items: list[HumanReviewItem]
