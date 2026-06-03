from fastapi import APIRouter, Query, status

from src.modules.delivery_milestones.schemas import (
    BuildDeliveryMilestonesRequest,
    DeliveryMilestoneEventResponse,
    DeliveryMilestoneRecordResponse,
    DeliveryMilestoneSetResponse,
    RegisterDeliveryMilestoneEventRequest,
)
from src.modules.delivery_milestones.service import (
    build_delivery_milestones,
    get_delivery_milestone_record,
    get_delivery_milestone_set,
    list_delivery_milestone_sets,
    register_delivery_milestone_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["delivery-milestones"])


def _to_event_response(item) -> DeliveryMilestoneEventResponse:
    return DeliveryMilestoneEventResponse.model_validate(item)


def _to_record_response(result: tuple) -> DeliveryMilestoneRecordResponse:
    record, events = result
    return DeliveryMilestoneRecordResponse(
        delivery_milestone_id=record.delivery_milestone_id,
        delivery_milestone_set_id=record.delivery_milestone_set_id,
        milestone_code=record.milestone_code,
        milestone_name=record.milestone_name,
        due_date=record.due_date,
        milestone_state=record.milestone_state,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[_to_event_response(item) for item in events],
    )


def _to_set_response(result: tuple) -> DeliveryMilestoneSetResponse:
    milestone_set, records = result
    return DeliveryMilestoneSetResponse(
        delivery_milestone_set_id=milestone_set.delivery_milestone_set_id,
        deal_id=milestone_set.deal_id,
        execution_command_set_id=milestone_set.execution_command_set_id,
        milestone_status=milestone_set.milestone_status,
        created_at=milestone_set.created_at,
        updated_at=milestone_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/delivery-milestones/build", response_model=DeliveryMilestoneSetResponse, status_code=status.HTTP_201_CREATED)
def build_delivery_milestones_route(
    payload: BuildDeliveryMilestonesRequest,
    session: DBSession,
) -> DeliveryMilestoneSetResponse:
    milestone_set = build_delivery_milestones(session, payload)
    return _to_set_response(get_delivery_milestone_set(session, milestone_set.delivery_milestone_set_id))


@router.post("/delivery-milestones/events", response_model=DeliveryMilestoneEventResponse, status_code=status.HTTP_201_CREATED)
def register_delivery_milestone_event_route(
    payload: RegisterDeliveryMilestoneEventRequest,
    session: DBSession,
) -> DeliveryMilestoneEventResponse:
    return _to_event_response(register_delivery_milestone_event(session, payload))


@router.get("/delivery-milestones/{delivery_milestone_set_id}", response_model=DeliveryMilestoneSetResponse)
def get_delivery_milestone_set_route(
    delivery_milestone_set_id: str,
    session: DBSession,
) -> DeliveryMilestoneSetResponse:
    return _to_set_response(get_delivery_milestone_set(session, delivery_milestone_set_id))


@router.get("/delivery-milestones", response_model=list[DeliveryMilestoneSetResponse])
def list_delivery_milestone_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[DeliveryMilestoneSetResponse]:
    return [_to_set_response(item) for item in list_delivery_milestone_sets(session, deal_id=deal_id)]


@router.get("/delivery-milestones/records/{delivery_milestone_id}", response_model=DeliveryMilestoneRecordResponse)
def get_delivery_milestone_record_route(
    delivery_milestone_id: str,
    session: DBSession,
) -> DeliveryMilestoneRecordResponse:
    return _to_record_response(get_delivery_milestone_record(session, delivery_milestone_id))
