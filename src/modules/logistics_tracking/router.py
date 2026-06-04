from fastapi import APIRouter, Query, status

from src.modules.logistics_tracking.schemas import (
    BuildLogisticsTrackingRequest,
    LogisticsTrackingEventResponse,
    LogisticsTrackingLinkResponse,
    LogisticsTrackingRecordResponse,
    LogisticsTrackingSetResponse,
    RegisterLogisticsTrackingEventRequest,
)
from src.modules.logistics_tracking.service import (
    build_logistics_tracking,
    get_logistics_tracking_record,
    get_logistics_tracking_set,
    list_logistics_tracking_sets,
    register_logistics_tracking_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["logistics-tracking"])


def _to_record_response(result: tuple) -> LogisticsTrackingRecordResponse:
    record, events, links = result
    return LogisticsTrackingRecordResponse(
        logistics_tracking_id=record.logistics_tracking_id,
        eta_at=record.eta_at,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[LogisticsTrackingEventResponse.model_validate(item) for item in events],
        links=[LogisticsTrackingLinkResponse.model_validate(item) for item in links],
    )


def _to_set_response(result: tuple) -> LogisticsTrackingSetResponse:
    tracking_set, records = result
    return LogisticsTrackingSetResponse(
        logistics_tracking_set_id=tracking_set.logistics_tracking_set_id,
        deal_id=tracking_set.deal_id,
        logistics_status=tracking_set.logistics_status,
        created_at=tracking_set.created_at,
        updated_at=tracking_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/logistics-tracking/build", response_model=LogisticsTrackingSetResponse, status_code=status.HTTP_201_CREATED)
def build_logistics_tracking_route(payload: BuildLogisticsTrackingRequest, session: DBSession) -> LogisticsTrackingSetResponse:
    tracking_set = build_logistics_tracking(session, payload)
    return _to_set_response(get_logistics_tracking_set(session, tracking_set.logistics_tracking_set_id))


@router.post("/logistics-tracking/events", response_model=LogisticsTrackingEventResponse, status_code=status.HTTP_201_CREATED)
def register_logistics_tracking_event_route(
    payload: RegisterLogisticsTrackingEventRequest,
    session: DBSession,
) -> LogisticsTrackingEventResponse:
    event = register_logistics_tracking_event(session, payload)
    return LogisticsTrackingEventResponse.model_validate(event)


@router.get("/logistics-tracking/{logistics_tracking_set_id}", response_model=LogisticsTrackingSetResponse)
def get_logistics_tracking_set_route(logistics_tracking_set_id: str, session: DBSession) -> LogisticsTrackingSetResponse:
    return _to_set_response(get_logistics_tracking_set(session, logistics_tracking_set_id))


@router.get("/logistics-tracking", response_model=list[LogisticsTrackingSetResponse])
def list_logistics_tracking_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[LogisticsTrackingSetResponse]:
    return [_to_set_response(item) for item in list_logistics_tracking_sets(session, deal_id=deal_id)]


@router.get("/logistics-tracking/records/{logistics_tracking_id}", response_model=LogisticsTrackingRecordResponse)
def get_logistics_tracking_record_route(logistics_tracking_id: str, session: DBSession) -> LogisticsTrackingRecordResponse:
    return _to_record_response(get_logistics_tracking_record(session, logistics_tracking_id))
