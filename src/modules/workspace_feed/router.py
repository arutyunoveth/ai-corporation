from fastapi import APIRouter, Query, status

from src.modules.workspace_feed.schemas import (
    BuildWorkspaceFeedRequest,
    WorkspaceFeedItemResponse,
    WorkspaceFeedRecordResponse,
    WorkspaceFeedSetResponse,
)
from src.modules.workspace_feed.service import (
    build_workspace_feed,
    get_workspace_feed_record,
    get_workspace_feed_set,
    list_workspace_feed_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkspaceScopeType

router = APIRouter(tags=["workspace-feed"])


def _to_item_response(item) -> WorkspaceFeedItemResponse:
    return WorkspaceFeedItemResponse.model_validate(item)


def _to_record_response(result: tuple) -> WorkspaceFeedRecordResponse:
    record, items = result
    return WorkspaceFeedRecordResponse(
        workspace_feed_id=record.workspace_feed_id,
        workspace_feed_set_id=record.workspace_feed_set_id,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[_to_item_response(item) for item in items],
    )


def _to_set_response(result: tuple) -> WorkspaceFeedSetResponse:
    feed_set, records = result
    return WorkspaceFeedSetResponse(
        workspace_feed_set_id=feed_set.workspace_feed_set_id,
        scope_type=feed_set.scope_type,
        scope_ref=feed_set.scope_ref,
        workspace_status=feed_set.workspace_status,
        created_at=feed_set.created_at,
        updated_at=feed_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/workspace-feed/build", response_model=WorkspaceFeedSetResponse, status_code=status.HTTP_201_CREATED)
def build_workspace_feed_route(payload: BuildWorkspaceFeedRequest, session: DBSession) -> WorkspaceFeedSetResponse:
    feed_set = build_workspace_feed(session, payload)
    return _to_set_response(get_workspace_feed_set(session, feed_set.workspace_feed_set_id))


@router.get("/workspace-feed/{workspace_feed_set_id}", response_model=WorkspaceFeedSetResponse)
def get_workspace_feed_set_route(workspace_feed_set_id: str, session: DBSession) -> WorkspaceFeedSetResponse:
    return _to_set_response(get_workspace_feed_set(session, workspace_feed_set_id))


@router.get("/workspace-feed", response_model=list[WorkspaceFeedSetResponse])
def list_workspace_feed_sets_route(
    session: DBSession,
    scope_type: WorkspaceScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[WorkspaceFeedSetResponse]:
    return [_to_set_response(item) for item in list_workspace_feed_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/workspace-feed/records/{workspace_feed_id}", response_model=WorkspaceFeedRecordResponse)
def get_workspace_feed_record_route(workspace_feed_id: str, session: DBSession) -> WorkspaceFeedRecordResponse:
    return _to_record_response(get_workspace_feed_record(session, workspace_feed_id))
