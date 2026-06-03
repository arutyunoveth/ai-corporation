from fastapi import APIRouter, Query, status

from src.modules.deal_closure.schemas import (
    BuildDealClosureRequest,
    CloseDealRequest,
    DealArchiveSnapshotResponse,
    DealClosureRecordResponse,
    DealClosureSetResponse,
)
from src.modules.deal_closure.service import (
    build_deal_closure,
    close_deal,
    get_deal_closure_record,
    get_deal_closure_set,
    list_deal_closure_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["deal-closure"])


def _to_snapshot_response(item) -> DealArchiveSnapshotResponse:
    return DealArchiveSnapshotResponse.model_validate(item)


def _to_record_response(item) -> DealClosureRecordResponse:
    return DealClosureRecordResponse.model_validate(item)


def _to_set_response(result: tuple) -> DealClosureSetResponse:
    closure_set, records, snapshots = result
    return DealClosureSetResponse(
        deal_closure_set_id=closure_set.deal_closure_set_id,
        deal_id=closure_set.deal_id,
        outcome_intake_set_id=closure_set.outcome_intake_set_id,
        execution_command_set_id=closure_set.execution_command_set_id,
        closure_status=closure_set.closure_status,
        created_at=closure_set.created_at,
        updated_at=closure_set.updated_at,
        records=[_to_record_response(item) for item in records],
        archive_snapshots=[_to_snapshot_response(item) for item in snapshots],
    )


@router.post("/deal-closure/build", response_model=DealClosureSetResponse, status_code=status.HTTP_201_CREATED)
def build_deal_closure_route(payload: BuildDealClosureRequest, session: DBSession) -> DealClosureSetResponse:
    closure_set = build_deal_closure(session, payload)
    return _to_set_response(get_deal_closure_set(session, closure_set.deal_closure_set_id))


@router.post("/deal-closure/close", response_model=DealClosureSetResponse)
def close_deal_route(payload: CloseDealRequest, session: DBSession) -> DealClosureSetResponse:
    closure_set = close_deal(session, payload)
    return _to_set_response(get_deal_closure_set(session, closure_set.deal_closure_set_id))


@router.get("/deal-closure/{deal_closure_set_id}", response_model=DealClosureSetResponse)
def get_deal_closure_set_route(deal_closure_set_id: str, session: DBSession) -> DealClosureSetResponse:
    return _to_set_response(get_deal_closure_set(session, deal_closure_set_id))


@router.get("/deal-closure", response_model=list[DealClosureSetResponse])
def list_deal_closure_sets_route(
    session: DBSession, deal_id: str | None = Query(default=None)
) -> list[DealClosureSetResponse]:
    return [_to_set_response(item) for item in list_deal_closure_sets(session, deal_id=deal_id)]


@router.get("/deal-closure/records/{deal_closure_id}", response_model=DealClosureRecordResponse)
def get_deal_closure_record_route(deal_closure_id: str, session: DBSession) -> DealClosureRecordResponse:
    return _to_record_response(get_deal_closure_record(session, deal_closure_id))
