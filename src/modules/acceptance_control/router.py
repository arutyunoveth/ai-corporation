from fastapi import APIRouter, Query, status

from src.modules.acceptance_control.schemas import (
    AcceptanceControlRecordResponse,
    AcceptanceControlSetResponse,
    AcceptanceRemarkResponse,
    AcceptanceResolutionItemResponse,
    BuildAcceptanceControlRequest,
)
from src.modules.acceptance_control.service import (
    build_acceptance_control,
    get_acceptance_control_record,
    get_acceptance_control_set,
    list_acceptance_control_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["acceptance-control"])


def _to_record_response(result: tuple) -> AcceptanceControlRecordResponse:
    record, remarks, resolution_items = result
    return AcceptanceControlRecordResponse(
        acceptance_control_id=record.acceptance_control_id,
        summary_text=record.summary_text,
        resolution_state=record.resolution_state,
        created_at=record.created_at,
        updated_at=record.updated_at,
        remarks=[AcceptanceRemarkResponse.model_validate(item) for item in remarks],
        resolution_items=[AcceptanceResolutionItemResponse.model_validate(item) for item in resolution_items],
    )


def _to_set_response(result: tuple) -> AcceptanceControlSetResponse:
    control_set, records = result
    return AcceptanceControlSetResponse(
        acceptance_control_set_id=control_set.acceptance_control_set_id,
        deal_id=control_set.deal_id,
        acceptance_status=control_set.acceptance_status,
        created_at=control_set.created_at,
        updated_at=control_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/acceptance-control/build", response_model=AcceptanceControlSetResponse, status_code=status.HTTP_201_CREATED)
def build_acceptance_control_route(payload: BuildAcceptanceControlRequest, session: DBSession) -> AcceptanceControlSetResponse:
    control_set = build_acceptance_control(session, payload)
    return _to_set_response(get_acceptance_control_set(session, control_set.acceptance_control_set_id))


@router.get("/acceptance-control/{acceptance_control_set_id}", response_model=AcceptanceControlSetResponse)
def get_acceptance_control_set_route(acceptance_control_set_id: str, session: DBSession) -> AcceptanceControlSetResponse:
    return _to_set_response(get_acceptance_control_set(session, acceptance_control_set_id))


@router.get("/acceptance-control", response_model=list[AcceptanceControlSetResponse])
def list_acceptance_control_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[AcceptanceControlSetResponse]:
    return [_to_set_response(item) for item in list_acceptance_control_sets(session, deal_id=deal_id)]


@router.get("/acceptance-control/records/{acceptance_control_id}", response_model=AcceptanceControlRecordResponse)
def get_acceptance_control_record_route(acceptance_control_id: str, session: DBSession) -> AcceptanceControlRecordResponse:
    return _to_record_response(get_acceptance_control_record(session, acceptance_control_id))
