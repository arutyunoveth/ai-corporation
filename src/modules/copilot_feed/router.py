from fastapi import APIRouter, Query, status

from src.modules.copilot_feed.schemas import (
    BuildCopilotFeedRequest,
    CopilotFeedItemResponse,
    CopilotFeedRecordResponse,
    CopilotFeedSetResponse,
)
from src.modules.copilot_feed.service import (
    build_copilot_feed,
    get_copilot_feed_record,
    get_copilot_feed_set,
    list_copilot_feed_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkflowScopeType

router = APIRouter(tags=["copilot-feed"])


def _to_item_response(item) -> CopilotFeedItemResponse:
    return CopilotFeedItemResponse.model_validate(item)


def _to_record_response(result: tuple) -> CopilotFeedRecordResponse:
    record, items = result
    return CopilotFeedRecordResponse(
        copilot_feed_id=record.copilot_feed_id,
        copilot_feed_set_id=record.copilot_feed_set_id,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[_to_item_response(item) for item in items],
    )


def _to_set_response(result: tuple) -> CopilotFeedSetResponse:
    feed_set, records = result
    return CopilotFeedSetResponse(
        copilot_feed_set_id=feed_set.copilot_feed_set_id,
        scope_type=feed_set.scope_type,
        scope_ref=feed_set.scope_ref,
        feed_status=feed_set.feed_status,
        created_at=feed_set.created_at,
        updated_at=feed_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/copilot-feed/build", response_model=CopilotFeedSetResponse, status_code=status.HTTP_201_CREATED)
def build_copilot_feed_route(payload: BuildCopilotFeedRequest, session: DBSession) -> CopilotFeedSetResponse:
    feed_set = build_copilot_feed(session, payload)
    return _to_set_response(get_copilot_feed_set(session, feed_set.copilot_feed_set_id))


@router.get("/copilot-feed/{copilot_feed_set_id}", response_model=CopilotFeedSetResponse)
def get_copilot_feed_set_route(copilot_feed_set_id: str, session: DBSession) -> CopilotFeedSetResponse:
    return _to_set_response(get_copilot_feed_set(session, copilot_feed_set_id))


@router.get("/copilot-feed", response_model=list[CopilotFeedSetResponse])
def list_copilot_feed_sets_route(
    session: DBSession,
    scope_type: WorkflowScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[CopilotFeedSetResponse]:
    return [_to_set_response(item) for item in list_copilot_feed_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/copilot-feed/records/{copilot_feed_id}", response_model=CopilotFeedRecordResponse)
def get_copilot_feed_record_route(copilot_feed_id: str, session: DBSession) -> CopilotFeedRecordResponse:
    return _to_record_response(get_copilot_feed_record(session, copilot_feed_id))
