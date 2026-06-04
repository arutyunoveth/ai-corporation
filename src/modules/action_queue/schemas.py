from datetime import datetime

from src.shared.enums import (
    ActionExecutionStatus,
    ActionQueueStatus,
    ActionType,
    QueueApprovalStatus,
    WorkspaceScopeType,
)
from src.shared.types.common import APIModel


class BuildActionQueueRequest(APIModel):
    scope_type: WorkspaceScopeType
    scope_ref: str


class ApproveActionQueueItemRequest(APIModel):
    action_queue_id: str
    approval_status: QueueApprovalStatus
    approved_by_ref: str
    rationale: str


class ActionQueueApprovalResponse(APIModel):
    action_queue_id: str
    approval_status: QueueApprovalStatus
    approved_by_ref: str
    rationale: str
    created_at: datetime
    updated_at: datetime


class ActionQueueRecordResponse(APIModel):
    action_queue_id: str
    action_queue_set_id: str
    action_code: str
    action_type: ActionType
    action_status: ActionExecutionStatus
    action_text: str
    source_ref: str | None
    created_at: datetime
    updated_at: datetime
    approvals: list[ActionQueueApprovalResponse]


class ActionQueueSetResponse(APIModel):
    action_queue_set_id: str
    scope_type: WorkspaceScopeType
    scope_ref: str
    queue_status: ActionQueueStatus
    created_at: datetime
    updated_at: datetime
    records: list[ActionQueueRecordResponse]
