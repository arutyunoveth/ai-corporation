from fastapi import APIRouter, Query, status

from src.modules.bid_completeness.schemas import (
    BidCompletenessFlagResponse,
    BidCompletenessRecordResponse,
    BidCompletenessSetResponse,
    CheckBidCompletenessRequest,
)
from src.modules.bid_completeness.service import (
    check_bid_completeness,
    get_bid_completeness_record,
    get_bid_completeness_set,
    list_bid_completeness_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["bid-completeness"])


def _to_record_response(result: tuple) -> BidCompletenessRecordResponse:
    record, flags = result
    return BidCompletenessRecordResponse(
        bid_completeness_id=record.bid_completeness_id,
        bid_completeness_set_id=record.bid_completeness_set_id,
        mandatory_total=record.mandatory_total,
        mandatory_present=record.mandatory_present,
        optional_present=record.optional_present,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        flags=[BidCompletenessFlagResponse.model_validate(item) for item in flags],
    )


def _to_set_response(result: tuple) -> BidCompletenessSetResponse:
    completeness_set, records = result
    return BidCompletenessSetResponse(
        bid_completeness_set_id=completeness_set.bid_completeness_set_id,
        deal_id=completeness_set.deal_id,
        bid_package_set_id=completeness_set.bid_package_set_id,
        completeness_status=completeness_set.completeness_status,
        created_at=completeness_set.created_at,
        updated_at=completeness_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/bid-completeness/check", response_model=BidCompletenessSetResponse, status_code=status.HTTP_201_CREATED)
def check_bid_completeness_route(
    payload: CheckBidCompletenessRequest,
    session: DBSession,
) -> BidCompletenessSetResponse:
    completeness_set = check_bid_completeness(session, payload)
    return _to_set_response(get_bid_completeness_set(session, completeness_set.bid_completeness_set_id))


@router.get("/bid-completeness/{bid_completeness_set_id}", response_model=BidCompletenessSetResponse)
def get_bid_completeness_set_route(
    bid_completeness_set_id: str,
    session: DBSession,
) -> BidCompletenessSetResponse:
    return _to_set_response(get_bid_completeness_set(session, bid_completeness_set_id))


@router.get("/bid-completeness", response_model=list[BidCompletenessSetResponse])
def list_bid_completeness_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[BidCompletenessSetResponse]:
    return [_to_set_response(item) for item in list_bid_completeness_sets(session, deal_id=deal_id)]


@router.get("/bid-completeness/records/{bid_completeness_id}", response_model=BidCompletenessRecordResponse)
def get_bid_completeness_record_route(
    bid_completeness_id: str,
    session: DBSession,
) -> BidCompletenessRecordResponse:
    return _to_record_response(get_bid_completeness_record(session, bid_completeness_id))
