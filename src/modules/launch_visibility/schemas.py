from datetime import datetime

from src.shared.enums import EventSeverity, LaunchVisibilityItemType, LaunchVisibilityScopeType, LaunchVisibilityStatus
from src.shared.types.common import APIModel


class BuildLaunchVisibilityRequest(APIModel):
    scope_type: LaunchVisibilityScopeType
    scope_ref: str


class LaunchVisibilityItemResponse(APIModel):
    deal_id: str | None
    item_code: str
    item_type: LaunchVisibilityItemType
    severity: EventSeverity
    source_module_id: str | None
    source_ref: str | None
    title: str
    detail_text: str
    requires_manual_review: bool
    created_at: datetime


class LaunchVisibilityRecordResponse(APIModel):
    launch_visibility_id: str
    launch_visibility_set_id: str
    summary_text: str
    active_deal_count: int
    blocked_deal_count: int
    attention_count: int
    red_flag_count: int
    manual_review_count: int
    overdue_count: int
    created_at: datetime
    updated_at: datetime
    items: list[LaunchVisibilityItemResponse]


class LaunchVisibilitySetResponse(APIModel):
    launch_visibility_set_id: str
    scope_type: LaunchVisibilityScopeType
    scope_ref: str
    visibility_status: LaunchVisibilityStatus
    created_at: datetime
    updated_at: datetime
    records: list[LaunchVisibilityRecordResponse]
