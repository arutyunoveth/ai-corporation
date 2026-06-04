from fastapi import APIRouter, Query, status

from src.modules.payment_tracking.schemas import (
    BuildPaymentTrackingRequest,
    PaymentTrackingAlertResponse,
    PaymentTrackingEventResponse,
    PaymentTrackingRecordResponse,
    PaymentTrackingSetResponse,
    RegisterPaymentTrackingEventRequest,
)
from src.modules.payment_tracking.service import (
    build_payment_tracking,
    get_payment_tracking_record,
    get_payment_tracking_set,
    list_payment_tracking_sets,
    register_payment_tracking_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["payment-tracking"])


def _to_record_response(result: tuple) -> PaymentTrackingRecordResponse:
    record, events, alerts = result
    return PaymentTrackingRecordResponse(
        payment_tracking_id=record.payment_tracking_id,
        expected_amount=record.expected_amount,
        paid_amount=record.paid_amount,
        overdue_days=record.overdue_days,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[PaymentTrackingEventResponse.model_validate(item) for item in events],
        alerts=[PaymentTrackingAlertResponse.model_validate(item) for item in alerts],
    )


def _to_set_response(result: tuple) -> PaymentTrackingSetResponse:
    tracking_set, records = result
    return PaymentTrackingSetResponse(
        payment_tracking_set_id=tracking_set.payment_tracking_set_id,
        deal_id=tracking_set.deal_id,
        payment_status=tracking_set.payment_status,
        created_at=tracking_set.created_at,
        updated_at=tracking_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/payment-tracking/build", response_model=PaymentTrackingSetResponse, status_code=status.HTTP_201_CREATED)
def build_payment_tracking_route(payload: BuildPaymentTrackingRequest, session: DBSession) -> PaymentTrackingSetResponse:
    tracking_set = build_payment_tracking(session, payload)
    return _to_set_response(get_payment_tracking_set(session, tracking_set.payment_tracking_set_id))


@router.post("/payment-tracking/events", response_model=PaymentTrackingEventResponse, status_code=status.HTTP_201_CREATED)
def register_payment_tracking_event_route(
    payload: RegisterPaymentTrackingEventRequest,
    session: DBSession,
) -> PaymentTrackingEventResponse:
    event = register_payment_tracking_event(session, payload)
    return PaymentTrackingEventResponse.model_validate(event)


@router.get("/payment-tracking/{payment_tracking_set_id}", response_model=PaymentTrackingSetResponse)
def get_payment_tracking_set_route(payment_tracking_set_id: str, session: DBSession) -> PaymentTrackingSetResponse:
    return _to_set_response(get_payment_tracking_set(session, payment_tracking_set_id))


@router.get("/payment-tracking", response_model=list[PaymentTrackingSetResponse])
def list_payment_tracking_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[PaymentTrackingSetResponse]:
    return [_to_set_response(item) for item in list_payment_tracking_sets(session, deal_id=deal_id)]


@router.get("/payment-tracking/records/{payment_tracking_id}", response_model=PaymentTrackingRecordResponse)
def get_payment_tracking_record_route(payment_tracking_id: str, session: DBSession) -> PaymentTrackingRecordResponse:
    return _to_record_response(get_payment_tracking_record(session, payment_tracking_id))
