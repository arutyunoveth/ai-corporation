from fastapi import APIRouter, Query, status

from src.modules.postmortems.schemas import (
    BuildPostmortemRequest,
    PostmortemActionItemResponse,
    PostmortemFindingResponse,
    PostmortemRecordResponse,
    PostmortemSetResponse,
)
from src.modules.postmortems.service import (
    build_postmortem,
    get_postmortem_record,
    get_postmortem_set,
    list_postmortem_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["postmortems"])


def _to_record_response(result: tuple) -> PostmortemRecordResponse:
    record, findings, action_items = result
    return PostmortemRecordResponse(
        postmortem_id=record.postmortem_id,
        summary_text=record.summary_text,
        root_cause_summary=record.root_cause_summary,
        recommendation_summary=record.recommendation_summary,
        created_at=record.created_at,
        updated_at=record.updated_at,
        findings=[PostmortemFindingResponse.model_validate(item) for item in findings],
        action_items=[PostmortemActionItemResponse.model_validate(item) for item in action_items],
    )


def _to_set_response(result: tuple) -> PostmortemSetResponse:
    postmortem_set, records = result
    return PostmortemSetResponse(
        postmortem_set_id=postmortem_set.postmortem_set_id,
        deal_id=postmortem_set.deal_id,
        deal_closure_report_set_id=postmortem_set.deal_closure_report_set_id,
        incident_register_set_id=postmortem_set.incident_register_set_id,
        claim_trigger_set_id=postmortem_set.claim_trigger_set_id,
        kpi_learning_set_id=postmortem_set.kpi_learning_set_id,
        postmortem_status=postmortem_set.postmortem_status,
        created_at=postmortem_set.created_at,
        updated_at=postmortem_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/postmortems/build", response_model=PostmortemSetResponse, status_code=status.HTTP_201_CREATED)
def build_postmortem_route(payload: BuildPostmortemRequest, session: DBSession) -> PostmortemSetResponse:
    postmortem_set = build_postmortem(session, payload)
    return _to_set_response(get_postmortem_set(session, postmortem_set.postmortem_set_id))


@router.get("/postmortems/{postmortem_set_id}", response_model=PostmortemSetResponse)
def get_postmortem_set_route(postmortem_set_id: str, session: DBSession) -> PostmortemSetResponse:
    return _to_set_response(get_postmortem_set(session, postmortem_set_id))


@router.get("/postmortems", response_model=list[PostmortemSetResponse])
def list_postmortem_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[PostmortemSetResponse]:
    return [_to_set_response(item) for item in list_postmortem_sets(session, deal_id=deal_id)]


@router.get("/postmortems/records/{postmortem_id}", response_model=PostmortemRecordResponse)
def get_postmortem_record_route(postmortem_id: str, session: DBSession) -> PostmortemRecordResponse:
    return _to_record_response(get_postmortem_record(session, postmortem_id))
