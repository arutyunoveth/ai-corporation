from fastapi import APIRouter, Query, status

from src.modules.action_console.schemas import (
    ActionConsoleItemResponse,
    ActionConsoleRecordResponse,
    ActionConsoleSetResponse,
    BuildActionConsoleRequest,
)
from src.modules.action_console.service import (
    build_action_console,
    get_action_console_record,
    get_action_console_set,
    list_action_console_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkspaceScopeType

router = APIRouter(tags=["action-console"])


def _to_item_response(item) -> ActionConsoleItemResponse:
    return ActionConsoleItemResponse.model_validate(item)


def _to_record_response(result: tuple) -> ActionConsoleRecordResponse:
    record, items = result
    return ActionConsoleRecordResponse(
        action_console_id=record.action_console_id,
        action_console_set_id=record.action_console_set_id,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[_to_item_response(item) for item in items],
    )


def _to_set_response(result: tuple) -> ActionConsoleSetResponse:
    console_set, records = result
    return ActionConsoleSetResponse(
        action_console_set_id=console_set.action_console_set_id,
        scope_type=console_set.scope_type,
        scope_ref=console_set.scope_ref,
        console_status=console_set.console_status,
        created_at=console_set.created_at,
        updated_at=console_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/action-console/build", response_model=ActionConsoleSetResponse, status_code=status.HTTP_201_CREATED)
def build_action_console_route(payload: BuildActionConsoleRequest, session: DBSession) -> ActionConsoleSetResponse:
    console_set = build_action_console(session, payload)
    return _to_set_response(get_action_console_set(session, console_set.action_console_set_id))


@router.get("/action-console/{action_console_set_id}", response_model=ActionConsoleSetResponse)
def get_action_console_set_route(action_console_set_id: str, session: DBSession) -> ActionConsoleSetResponse:
    return _to_set_response(get_action_console_set(session, action_console_set_id))


@router.get("/action-console", response_model=list[ActionConsoleSetResponse])
def list_action_console_sets_route(
    session: DBSession,
    scope_type: WorkspaceScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[ActionConsoleSetResponse]:
    return [_to_set_response(item) for item in list_action_console_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/action-console/records/{action_console_id}", response_model=ActionConsoleRecordResponse)
def get_action_console_record_route(action_console_id: str, session: DBSession) -> ActionConsoleRecordResponse:
    return _to_record_response(get_action_console_record(session, action_console_id))
