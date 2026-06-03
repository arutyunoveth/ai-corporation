from datetime import datetime

from src.shared.enums import CopilotFeedItemType, CopilotFeedStatus, CopilotPriority, WorkflowScopeType
from src.shared.types.common import APIModel


class BuildCopilotFeedRequest(APIModel):
    scope_type: WorkflowScopeType
    scope_ref: str


class CopilotFeedItemResponse(APIModel):
    item_code: str
    item_type: CopilotFeedItemType
    priority: CopilotPriority
    item_text: str
    source_ref: str | None
    created_at: datetime


class CopilotFeedRecordResponse(APIModel):
    copilot_feed_id: str
    copilot_feed_set_id: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    items: list[CopilotFeedItemResponse]


class CopilotFeedSetResponse(APIModel):
    copilot_feed_set_id: str
    scope_type: WorkflowScopeType
    scope_ref: str
    feed_status: CopilotFeedStatus
    created_at: datetime
    updated_at: datetime
    records: list[CopilotFeedRecordResponse]
