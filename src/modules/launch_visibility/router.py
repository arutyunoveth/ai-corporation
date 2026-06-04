from fastapi import APIRouter, Query, status

from src.modules.launch_visibility.schemas import (
    BuildLaunchVisibilityRequest,
    LaunchVisibilityItemResponse,
    LaunchVisibilityRecordResponse,
    LaunchVisibilitySetResponse,
)
from src.modules.launch_visibility.service import (
    build_launch_visibility,
    get_launch_visibility_record,
    get_launch_visibility_set,
    list_launch_visibility_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import LaunchVisibilityScopeType

router = APIRouter(tags=["launch-visibility"])


def _to_item_response(item) -> LaunchVisibilityItemResponse:
    return LaunchVisibilityItemResponse.model_validate(item)


def _to_record_response(result: tuple) -> LaunchVisibilityRecordResponse:
    record, items = result
    return LaunchVisibilityRecordResponse(
        launch_visibility_id=record.launch_visibility_id,
        launch_visibility_set_id=record.launch_visibility_set_id,
        summary_text=record.summary_text,
        active_deal_count=record.active_deal_count,
        blocked_deal_count=record.blocked_deal_count,
        attention_count=record.attention_count,
        red_flag_count=record.red_flag_count,
        manual_review_count=record.manual_review_count,
        overdue_count=record.overdue_count,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[_to_item_response(item) for item in items],
    )


def _to_set_response(result: tuple) -> LaunchVisibilitySetResponse:
    visibility_set, records = result
    return LaunchVisibilitySetResponse(
        launch_visibility_set_id=visibility_set.launch_visibility_set_id,
        scope_type=visibility_set.scope_type,
        scope_ref=visibility_set.scope_ref,
        visibility_status=visibility_set.visibility_status,
        created_at=visibility_set.created_at,
        updated_at=visibility_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/launch-visibility/build", response_model=LaunchVisibilitySetResponse, status_code=status.HTTP_201_CREATED)
def build_launch_visibility_route(
    payload: BuildLaunchVisibilityRequest,
    session: DBSession,
) -> LaunchVisibilitySetResponse:
    visibility_set = build_launch_visibility(session, payload.scope_type, payload.scope_ref)
    return _to_set_response(get_launch_visibility_set(session, visibility_set.launch_visibility_set_id))


@router.get("/launch-visibility/{launch_visibility_set_id}", response_model=LaunchVisibilitySetResponse)
def get_launch_visibility_set_route(launch_visibility_set_id: str, session: DBSession) -> LaunchVisibilitySetResponse:
    return _to_set_response(get_launch_visibility_set(session, launch_visibility_set_id))


@router.get("/launch-visibility", response_model=list[LaunchVisibilitySetResponse])
def list_launch_visibility_sets_route(
    session: DBSession,
    scope_type: LaunchVisibilityScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[LaunchVisibilitySetResponse]:
    return [_to_set_response(item) for item in list_launch_visibility_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/launch-visibility/records/{launch_visibility_id}", response_model=LaunchVisibilityRecordResponse)
def get_launch_visibility_record_route(launch_visibility_id: str, session: DBSession) -> LaunchVisibilityRecordResponse:
    return _to_record_response(get_launch_visibility_record(session, launch_visibility_id))
