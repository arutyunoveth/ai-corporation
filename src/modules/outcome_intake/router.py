from fastapi import APIRouter, Query, status

from src.modules.outcome_intake.schemas import (
    OutcomeIntakeBindingResponse,
    OutcomeIntakeRecordResponse,
    OutcomeIntakeSetResponse,
    RegisterOutcomeIntakeRequest,
)
from src.modules.outcome_intake.service import (
    get_outcome_intake_record,
    get_outcome_intake_set,
    list_outcome_intake_sets,
    register_outcome_intake,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["outcome-intake"])


def _to_binding_response(item) -> OutcomeIntakeBindingResponse:
    return OutcomeIntakeBindingResponse.model_validate(item)


def _to_record_response(result: tuple) -> OutcomeIntakeRecordResponse:
    record, bindings = result
    return OutcomeIntakeRecordResponse(
        outcome_intake_id=record.outcome_intake_id,
        outcome_intake_set_id=record.outcome_intake_set_id,
        outcome_code=record.outcome_code,
        effective_at=record.effective_at,
        rationale=record.rationale,
        created_at=record.created_at,
        updated_at=record.updated_at,
        bindings=[_to_binding_response(item) for item in bindings],
    )


def _to_set_response(result: tuple) -> OutcomeIntakeSetResponse:
    outcome_set, records = result
    return OutcomeIntakeSetResponse(
        outcome_intake_set_id=outcome_set.outcome_intake_set_id,
        deal_id=outcome_set.deal_id,
        post_submission_tracker_set_id=outcome_set.post_submission_tracker_set_id,
        outcome_status=outcome_set.outcome_status,
        created_at=outcome_set.created_at,
        updated_at=outcome_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/outcome-intake/register", response_model=OutcomeIntakeSetResponse, status_code=status.HTTP_201_CREATED)
def register_outcome_intake_route(
    payload: RegisterOutcomeIntakeRequest,
    session: DBSession,
) -> OutcomeIntakeSetResponse:
    outcome_set = register_outcome_intake(session, payload)
    return _to_set_response(get_outcome_intake_set(session, outcome_set.outcome_intake_set_id))


@router.get("/outcome-intake/{outcome_intake_set_id}", response_model=OutcomeIntakeSetResponse)
def get_outcome_intake_set_route(
    outcome_intake_set_id: str,
    session: DBSession,
) -> OutcomeIntakeSetResponse:
    return _to_set_response(get_outcome_intake_set(session, outcome_intake_set_id))


@router.get("/outcome-intake", response_model=list[OutcomeIntakeSetResponse])
def list_outcome_intake_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[OutcomeIntakeSetResponse]:
    return [_to_set_response(item) for item in list_outcome_intake_sets(session, deal_id=deal_id)]


@router.get("/outcome-intake/records/{outcome_intake_id}", response_model=OutcomeIntakeRecordResponse)
def get_outcome_intake_record_route(
    outcome_intake_id: str,
    session: DBSession,
) -> OutcomeIntakeRecordResponse:
    return _to_record_response(get_outcome_intake_record(session, outcome_intake_id))
