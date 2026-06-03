from fastapi import APIRouter, Query, status

from src.modules.cash_gap.schemas import BuildCashGapRequest, CashGapRecordResponse, CashGapScenarioResponse, CashGapSetResponse
from src.modules.cash_gap.service import build_cash_gap, get_cash_gap_record, get_cash_gap_set, list_cash_gap_sets
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["cash-gap"])


def _to_record_response(result: tuple) -> CashGapRecordResponse:
    record, scenarios = result
    return CashGapRecordResponse(
        cash_gap_id=record.cash_gap_id,
        cash_gap_set_id=record.cash_gap_set_id,
        peak_gap_amount=record.peak_gap_amount,
        gap_duration_days=record.gap_duration_days,
        currency_code=record.currency_code,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        scenarios=[CashGapScenarioResponse.model_validate(item) for item in scenarios],
    )


def _to_set_response(result: tuple) -> CashGapSetResponse:
    cash_gap_set, records = result
    return CashGapSetResponse(
        cash_gap_set_id=cash_gap_set.cash_gap_set_id,
        deal_id=cash_gap_set.deal_id,
        cost_model_set_id=cash_gap_set.cost_model_set_id,
        cash_gap_status=cash_gap_set.cash_gap_status,
        created_at=cash_gap_set.created_at,
        updated_at=cash_gap_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/cash-gap/build", response_model=CashGapSetResponse, status_code=status.HTTP_201_CREATED)
def build_cash_gap_route(payload: BuildCashGapRequest, session: DBSession) -> CashGapSetResponse:
    cash_gap_set = build_cash_gap(session, payload)
    return _to_set_response(get_cash_gap_set(session, cash_gap_set.cash_gap_set_id))


@router.get("/cash-gap/{cash_gap_set_id}", response_model=CashGapSetResponse)
def get_cash_gap_set_route(cash_gap_set_id: str, session: DBSession) -> CashGapSetResponse:
    return _to_set_response(get_cash_gap_set(session, cash_gap_set_id))


@router.get("/cash-gap", response_model=list[CashGapSetResponse])
def list_cash_gap_sets_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[CashGapSetResponse]:
    return [_to_set_response(item) for item in list_cash_gap_sets(session, deal_id=deal_id)]


@router.get("/cash-gap/records/{cash_gap_id}", response_model=CashGapRecordResponse)
def get_cash_gap_record_route(cash_gap_id: str, session: DBSession) -> CashGapRecordResponse:
    return _to_record_response(get_cash_gap_record(session, cash_gap_id))
