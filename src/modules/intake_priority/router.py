from fastapi import APIRouter, Query, status

from src.modules.intake_priority.schemas import (
    BuildIntakePriorityRequest,
    IntakePriorityFactorResponse,
    IntakePriorityRecordResponse,
    IntakePrioritySetResponse,
)
from src.modules.intake_priority.service import (
    build_intake_priority,
    get_intake_priority_record,
    get_intake_priority_set,
    list_intake_priority_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["intake-priority"])


def _to_factor_response(item) -> IntakePriorityFactorResponse:
    return IntakePriorityFactorResponse.model_validate(item)


def _to_record_response(result: tuple) -> IntakePriorityRecordResponse:
    record, factors = result
    return IntakePriorityRecordResponse(
        intake_priority_id=record.intake_priority_id,
        intake_priority_set_id=record.intake_priority_set_id,
        priority_score=record.priority_score,
        summary_text=record.summary_text,
        recommended_queue_position=record.recommended_queue_position,
        created_at=record.created_at,
        updated_at=record.updated_at,
        factors=[_to_factor_response(item) for item in factors],
    )


def _to_set_response(result: tuple) -> IntakePrioritySetResponse:
    priority_set, records = result
    return IntakePrioritySetResponse(
        intake_priority_set_id=priority_set.intake_priority_set_id,
        deal_id=priority_set.deal_id,
        prioritization_status=priority_set.prioritization_status,
        created_at=priority_set.created_at,
        updated_at=priority_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/intake-priority/build", response_model=IntakePrioritySetResponse, status_code=status.HTTP_201_CREATED)
def build_intake_priority_route(payload: BuildIntakePriorityRequest, session: DBSession) -> IntakePrioritySetResponse:
    priority_set = build_intake_priority(session, payload.deal_id)
    return _to_set_response(get_intake_priority_set(session, priority_set.intake_priority_set_id))


@router.get("/intake-priority/{intake_priority_set_id}", response_model=IntakePrioritySetResponse)
def get_intake_priority_set_route(intake_priority_set_id: str, session: DBSession) -> IntakePrioritySetResponse:
    return _to_set_response(get_intake_priority_set(session, intake_priority_set_id))


@router.get("/intake-priority", response_model=list[IntakePrioritySetResponse])
def list_intake_priority_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[IntakePrioritySetResponse]:
    return [_to_set_response(item) for item in list_intake_priority_sets(session, deal_id=deal_id)]


@router.get("/intake-priority/records/{intake_priority_id}", response_model=IntakePriorityRecordResponse)
def get_intake_priority_record_route(intake_priority_id: str, session: DBSession) -> IntakePriorityRecordResponse:
    return _to_record_response(get_intake_priority_record(session, intake_priority_id))
