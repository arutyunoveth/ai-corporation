from fastapi import APIRouter, Query, status

from src.modules.action_queue.schemas import (
    ActionQueueApprovalResponse,
    ActionQueueRecordResponse,
    ActionQueueSetResponse,
    ApproveActionQueueItemRequest,
    BuildActionQueueRequest,
)
from src.modules.action_queue.service import (
    approve_action_queue_item,
    build_action_queue,
    get_action_queue_record,
    get_action_queue_set,
    list_action_queue_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkspaceScopeType

router = APIRouter(tags=["action-queue"])


def _to_approval_response(item) -> ActionQueueApprovalResponse:
    return ActionQueueApprovalResponse.model_validate(item)


def _to_record_response(result: tuple) -> ActionQueueRecordResponse:
    record, approvals = result
    return ActionQueueRecordResponse(
        action_queue_id=record.action_queue_id,
        action_queue_set_id=record.action_queue_set_id,
        action_code=record.action_code,
        action_type=record.action_type,
        action_status=record.action_status,
        action_text=record.action_text,
        source_ref=record.source_ref,
        created_at=record.created_at,
        updated_at=record.updated_at,
        approvals=[_to_approval_response(item) for item in approvals],
    )


def _to_set_response(result: tuple) -> ActionQueueSetResponse:
    queue_set, records = result
    return ActionQueueSetResponse(
        action_queue_set_id=queue_set.action_queue_set_id,
        scope_type=queue_set.scope_type,
        scope_ref=queue_set.scope_ref,
        queue_status=queue_set.queue_status,
        created_at=queue_set.created_at,
        updated_at=queue_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/action-queue/build", response_model=ActionQueueSetResponse, status_code=status.HTTP_201_CREATED)
def build_action_queue_route(payload: BuildActionQueueRequest, session: DBSession) -> ActionQueueSetResponse:
    queue_set = build_action_queue(session, payload)
    return _to_set_response(get_action_queue_set(session, queue_set.action_queue_set_id))


@router.post("/action-queue/approve", response_model=ActionQueueRecordResponse, status_code=status.HTTP_201_CREATED)
def approve_action_queue_item_route(
    payload: ApproveActionQueueItemRequest,
    session: DBSession,
) -> ActionQueueRecordResponse:
    approval = approve_action_queue_item(session, payload)
    return _to_record_response(get_action_queue_record(session, approval.action_queue_id))


@router.get("/action-queue/{action_queue_set_id}", response_model=ActionQueueSetResponse)
def get_action_queue_set_route(action_queue_set_id: str, session: DBSession) -> ActionQueueSetResponse:
    return _to_set_response(get_action_queue_set(session, action_queue_set_id))


@router.get("/action-queue", response_model=list[ActionQueueSetResponse])
def list_action_queue_sets_route(
    session: DBSession,
    scope_type: WorkspaceScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[ActionQueueSetResponse]:
    return [_to_set_response(item) for item in list_action_queue_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/action-queue/records/{action_queue_id}", response_model=ActionQueueRecordResponse)
def get_action_queue_record_route(action_queue_id: str, session: DBSession) -> ActionQueueRecordResponse:
    return _to_record_response(get_action_queue_record(session, action_queue_id))
