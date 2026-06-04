from datetime import datetime

from src.shared.enums import (
    ActionConsoleItemType,
    ActionConsolePriority,
    ActionConsoleStatus,
    WorkspaceScopeType,
)
from src.shared.types.common import APIModel


class BuildActionConsoleRequest(APIModel):
    scope_type: WorkspaceScopeType
    scope_ref: str


class ActionConsoleItemResponse(APIModel):
    item_code: str
    item_type: ActionConsoleItemType
    priority: ActionConsolePriority
    source_ref: str | None
    item_text: str
    created_at: datetime


class ActionConsoleRecordResponse(APIModel):
    action_console_id: str
    action_console_set_id: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    items: list[ActionConsoleItemResponse]


class ActionConsoleSetResponse(APIModel):
    action_console_set_id: str
    scope_type: WorkspaceScopeType
    scope_ref: str
    console_status: ActionConsoleStatus
    created_at: datetime
    updated_at: datetime
    records: list[ActionConsoleRecordResponse]
