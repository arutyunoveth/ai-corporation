from fastapi import APIRouter, Query, status

from src.modules.delivery_launch.schemas import (
    BuildDeliveryLaunchRequest,
    DeliveryLaunchFlagResponse,
    DeliveryLaunchRecordResponse,
    DeliveryLaunchSetResponse,
    LaunchDeliveryRequest,
)
from src.modules.delivery_launch.service import (
    build_delivery_launch,
    get_delivery_launch_record,
    get_delivery_launch_set,
    launch_delivery,
    list_delivery_launch_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["delivery-launch"])


def _to_flag_response(item) -> DeliveryLaunchFlagResponse:
    return DeliveryLaunchFlagResponse.model_validate(item)


def _to_record_response(result: tuple) -> DeliveryLaunchRecordResponse:
    record, flags = result
    return DeliveryLaunchRecordResponse(
        delivery_launch_id=record.delivery_launch_id,
        delivery_launch_set_id=record.delivery_launch_set_id,
        launch_recommendation=record.launch_recommendation,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        flags=[_to_flag_response(item) for item in flags],
    )


def _to_set_response(result: tuple) -> DeliveryLaunchSetResponse:
    launch_set, records = result
    return DeliveryLaunchSetResponse(
        delivery_launch_set_id=launch_set.delivery_launch_set_id,
        deal_id=launch_set.deal_id,
        outcome_intake_set_id=launch_set.outcome_intake_set_id,
        launch_status=launch_set.launch_status,
        created_at=launch_set.created_at,
        updated_at=launch_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/delivery-launch/build", response_model=DeliveryLaunchSetResponse, status_code=status.HTTP_201_CREATED)
def build_delivery_launch_route(
    payload: BuildDeliveryLaunchRequest,
    session: DBSession,
) -> DeliveryLaunchSetResponse:
    launch_set = build_delivery_launch(session, payload)
    return _to_set_response(get_delivery_launch_set(session, launch_set.delivery_launch_set_id))


@router.post("/delivery-launch/launch", response_model=DeliveryLaunchSetResponse)
def launch_delivery_route(
    payload: LaunchDeliveryRequest,
    session: DBSession,
) -> DeliveryLaunchSetResponse:
    launch_set = launch_delivery(session, payload)
    return _to_set_response(get_delivery_launch_set(session, launch_set.delivery_launch_set_id))


@router.get("/delivery-launch/{delivery_launch_set_id}", response_model=DeliveryLaunchSetResponse)
def get_delivery_launch_set_route(
    delivery_launch_set_id: str,
    session: DBSession,
) -> DeliveryLaunchSetResponse:
    return _to_set_response(get_delivery_launch_set(session, delivery_launch_set_id))


@router.get("/delivery-launch", response_model=list[DeliveryLaunchSetResponse])
def list_delivery_launch_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[DeliveryLaunchSetResponse]:
    return [_to_set_response(item) for item in list_delivery_launch_sets(session, deal_id=deal_id)]


@router.get("/delivery-launch/records/{delivery_launch_id}", response_model=DeliveryLaunchRecordResponse)
def get_delivery_launch_record_route(
    delivery_launch_id: str,
    session: DBSession,
) -> DeliveryLaunchRecordResponse:
    return _to_record_response(get_delivery_launch_record(session, delivery_launch_id))
