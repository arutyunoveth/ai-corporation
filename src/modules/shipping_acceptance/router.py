from fastapi import APIRouter, Query, status

from src.modules.shipping_acceptance.schemas import (
    BuildShippingAcceptanceRequest,
    RegisterShippingAcceptanceEventRequest,
    ShippingAcceptanceEventResponse,
    ShippingAcceptanceRecordResponse,
    ShippingAcceptanceSetResponse,
)
from src.modules.shipping_acceptance.service import (
    build_shipping_acceptance,
    get_shipping_acceptance_record,
    get_shipping_acceptance_set,
    list_shipping_acceptance_sets,
    register_shipping_acceptance_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["shipping-acceptance"])


def _to_event_response(item) -> ShippingAcceptanceEventResponse:
    return ShippingAcceptanceEventResponse.model_validate(item)


def _to_record_response(result: tuple) -> ShippingAcceptanceRecordResponse:
    record, events = result
    return ShippingAcceptanceRecordResponse(
        shipping_acceptance_id=record.shipping_acceptance_id,
        shipping_acceptance_set_id=record.shipping_acceptance_set_id,
        shipment_ref=record.shipment_ref,
        acceptance_ref=record.acceptance_ref,
        current_state=record.current_state,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[_to_event_response(item) for item in events],
    )


def _to_set_response(result: tuple) -> ShippingAcceptanceSetResponse:
    shipping_set, records = result
    return ShippingAcceptanceSetResponse(
        shipping_acceptance_set_id=shipping_set.shipping_acceptance_set_id,
        deal_id=shipping_set.deal_id,
        execution_command_set_id=shipping_set.execution_command_set_id,
        shipping_status=shipping_set.shipping_status,
        created_at=shipping_set.created_at,
        updated_at=shipping_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/shipping-acceptance/build", response_model=ShippingAcceptanceSetResponse, status_code=status.HTTP_201_CREATED)
def build_shipping_acceptance_route(
    payload: BuildShippingAcceptanceRequest,
    session: DBSession,
) -> ShippingAcceptanceSetResponse:
    shipping_set = build_shipping_acceptance(session, payload)
    return _to_set_response(get_shipping_acceptance_set(session, shipping_set.shipping_acceptance_set_id))


@router.post("/shipping-acceptance/events", response_model=ShippingAcceptanceEventResponse, status_code=status.HTTP_201_CREATED)
def register_shipping_acceptance_event_route(
    payload: RegisterShippingAcceptanceEventRequest,
    session: DBSession,
) -> ShippingAcceptanceEventResponse:
    return _to_event_response(register_shipping_acceptance_event(session, payload))


@router.get("/shipping-acceptance/{shipping_acceptance_set_id}", response_model=ShippingAcceptanceSetResponse)
def get_shipping_acceptance_set_route(
    shipping_acceptance_set_id: str,
    session: DBSession,
) -> ShippingAcceptanceSetResponse:
    return _to_set_response(get_shipping_acceptance_set(session, shipping_acceptance_set_id))


@router.get("/shipping-acceptance", response_model=list[ShippingAcceptanceSetResponse])
def list_shipping_acceptance_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ShippingAcceptanceSetResponse]:
    return [_to_set_response(item) for item in list_shipping_acceptance_sets(session, deal_id=deal_id)]


@router.get("/shipping-acceptance/records/{shipping_acceptance_id}", response_model=ShippingAcceptanceRecordResponse)
def get_shipping_acceptance_record_route(
    shipping_acceptance_id: str,
    session: DBSession,
) -> ShippingAcceptanceRecordResponse:
    return _to_record_response(get_shipping_acceptance_record(session, shipping_acceptance_id))
