from datetime import datetime

from src.shared.enums import (
    WorkspaceItemType,
    WorkspacePriority,
    WorkspaceScopeType,
    WorkspaceStatus,
)
from src.shared.types.common import APIModel


class BuildWorkspaceFeedRequest(APIModel):
    scope_type: WorkspaceScopeType
    scope_ref: str


class WorkspaceFeedItemResponse(APIModel):
    item_code: str
    item_type: WorkspaceItemType
    priority: WorkspacePriority
    item_text: str
    source_ref: str | None
    created_at: datetime


class WorkspaceFeedRecordResponse(APIModel):
    workspace_feed_id: str
    workspace_feed_set_id: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    items: list[WorkspaceFeedItemResponse]


class WorkspaceFeedSetResponse(APIModel):
    workspace_feed_set_id: str
    scope_type: WorkspaceScopeType
    scope_ref: str
    workspace_status: WorkspaceStatus
    created_at: datetime
    updated_at: datetime
    records: list[WorkspaceFeedRecordResponse]
