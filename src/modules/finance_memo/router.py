from fastapi import APIRouter, Query, status

from src.modules.finance_memo.schemas import BuildFinanceMemoRequest, FinanceMemoFlagResponse, FinanceMemoRecordResponse, FinanceMemoSetResponse
from src.modules.finance_memo.service import build_finance_memo, get_finance_memo_record, get_finance_memo_set, list_finance_memo_sets
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["finance-memo"])


def _to_record_response(result: tuple) -> FinanceMemoRecordResponse:
    record, flags = result
    return FinanceMemoRecordResponse(
        finance_memo_id=record.finance_memo_id,
        finance_memo_set_id=record.finance_memo_set_id,
        summary_text=record.summary_text,
        structured_summary_json=record.structured_summary_json,
        recommendation=record.recommendation,
        created_at=record.created_at,
        updated_at=record.updated_at,
        flags=[FinanceMemoFlagResponse.model_validate(item) for item in flags],
    )


def _to_set_response(result: tuple) -> FinanceMemoSetResponse:
    memo_set, records = result
    return FinanceMemoSetResponse(
        finance_memo_set_id=memo_set.finance_memo_set_id,
        deal_id=memo_set.deal_id,
        cost_model_set_id=memo_set.cost_model_set_id,
        cash_gap_set_id=memo_set.cash_gap_set_id,
        financing_strategy_set_id=memo_set.financing_strategy_set_id,
        memo_status=memo_set.memo_status,
        created_at=memo_set.created_at,
        updated_at=memo_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/finance-memo/build", response_model=FinanceMemoSetResponse, status_code=status.HTTP_201_CREATED)
def build_finance_memo_route(payload: BuildFinanceMemoRequest, session: DBSession) -> FinanceMemoSetResponse:
    memo_set = build_finance_memo(session, payload)
    return _to_set_response(get_finance_memo_set(session, memo_set.finance_memo_set_id))


@router.get("/finance-memo/{finance_memo_set_id}", response_model=FinanceMemoSetResponse)
def get_finance_memo_set_route(finance_memo_set_id: str, session: DBSession) -> FinanceMemoSetResponse:
    return _to_set_response(get_finance_memo_set(session, finance_memo_set_id))


@router.get("/finance-memo", response_model=list[FinanceMemoSetResponse])
def list_finance_memo_sets_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[FinanceMemoSetResponse]:
    return [_to_set_response(item) for item in list_finance_memo_sets(session, deal_id=deal_id)]


@router.get("/finance-memo/records/{finance_memo_id}", response_model=FinanceMemoRecordResponse)
def get_finance_memo_record_route(finance_memo_id: str, session: DBSession) -> FinanceMemoRecordResponse:
    return _to_record_response(get_finance_memo_record(session, finance_memo_id))
