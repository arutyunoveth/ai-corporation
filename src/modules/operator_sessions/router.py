from fastapi import APIRouter, Query, status

from src.modules.operator_sessions.schemas import (
    AcknowledgeOperatorSessionItemRequest,
    BuildOperatorSessionRequest,
    OperatorSessionItemResponse,
    OperatorSessionRecordResponse,
    OperatorSessionSetResponse,
)
from src.modules.operator_sessions.service import (
    acknowledge_operator_session_item,
    build_operator_session,
    get_operator_session_record,
    get_operator_session_set,
    list_operator_session_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkspaceScopeType

router = APIRouter(tags=["operator-sessions"])


def _to_item_response(item) -> OperatorSessionItemResponse:
    return OperatorSessionItemResponse.model_validate(item)


def _to_record_response(result: tuple) -> OperatorSessionRecordResponse:
    record, items = result
    return OperatorSessionRecordResponse(
        operator_session_id=record.operator_session_id,
        operator_session_set_id=record.operator_session_set_id,
        opened_by_ref=record.opened_by_ref,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[_to_item_response(item) for item in items],
    )


def _to_set_response(result: tuple) -> OperatorSessionSetResponse:
    session_set, records = result
    return OperatorSessionSetResponse(
        operator_session_set_id=session_set.operator_session_set_id,
        scope_type=session_set.scope_type,
        scope_ref=session_set.scope_ref,
        session_status=session_set.session_status,
        created_at=session_set.created_at,
        updated_at=session_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/operator-sessions/build", response_model=OperatorSessionSetResponse, status_code=status.HTTP_201_CREATED)
def build_operator_session_route(
    payload: BuildOperatorSessionRequest,
    session: DBSession,
) -> OperatorSessionSetResponse:
    session_set = build_operator_session(session, payload)
    return _to_set_response(get_operator_session_set(session, session_set.operator_session_set_id))


@router.post("/operator-sessions/items/ack", response_model=OperatorSessionRecordResponse, status_code=status.HTTP_201_CREATED)
def acknowledge_operator_session_item_route(
    payload: AcknowledgeOperatorSessionItemRequest,
    session: DBSession,
) -> OperatorSessionRecordResponse:
    item = acknowledge_operator_session_item(session, payload)
    return _to_record_response(get_operator_session_record(session, item.operator_session_id))


@router.get("/operator-sessions/{operator_session_set_id}", response_model=OperatorSessionSetResponse)
def get_operator_session_set_route(operator_session_set_id: str, session: DBSession) -> OperatorSessionSetResponse:
    return _to_set_response(get_operator_session_set(session, operator_session_set_id))


@router.get("/operator-sessions", response_model=list[OperatorSessionSetResponse])
def list_operator_session_sets_route(
    session: DBSession,
    scope_type: WorkspaceScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[OperatorSessionSetResponse]:
    return [_to_set_response(item) for item in list_operator_session_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/operator-sessions/records/{operator_session_id}", response_model=OperatorSessionRecordResponse)
def get_operator_session_record_route(operator_session_id: str, session: DBSession) -> OperatorSessionRecordResponse:
    return _to_record_response(get_operator_session_record(session, operator_session_id))
