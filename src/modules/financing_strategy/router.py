from fastapi import APIRouter, Query, status

from src.modules.financing_strategy.schemas import (
    BuildFinancingStrategyRequest,
    FinancingStrategyOptionResponse,
    FinancingStrategyRecordResponse,
    FinancingStrategySetResponse,
)
from src.modules.financing_strategy.service import (
    build_financing_strategy,
    get_financing_strategy_record,
    get_financing_strategy_set,
    list_financing_strategy_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["financing-strategy"])


def _to_record_response(result: tuple) -> FinancingStrategyRecordResponse:
    record, options = result
    return FinancingStrategyRecordResponse(
        financing_strategy_id=record.financing_strategy_id,
        financing_strategy_set_id=record.financing_strategy_set_id,
        recommended_option_code=record.recommended_option_code,
        feasible=record.feasible,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        options=[FinancingStrategyOptionResponse.model_validate(item) for item in options],
    )


def _to_set_response(result: tuple) -> FinancingStrategySetResponse:
    strategy_set, records = result
    return FinancingStrategySetResponse(
        financing_strategy_set_id=strategy_set.financing_strategy_set_id,
        deal_id=strategy_set.deal_id,
        cash_gap_set_id=strategy_set.cash_gap_set_id,
        strategy_status=strategy_set.strategy_status,
        created_at=strategy_set.created_at,
        updated_at=strategy_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/financing-strategy/build", response_model=FinancingStrategySetResponse, status_code=status.HTTP_201_CREATED)
def build_financing_strategy_route(payload: BuildFinancingStrategyRequest, session: DBSession) -> FinancingStrategySetResponse:
    strategy_set = build_financing_strategy(session, payload)
    return _to_set_response(get_financing_strategy_set(session, strategy_set.financing_strategy_set_id))


@router.get("/financing-strategy/{financing_strategy_set_id}", response_model=FinancingStrategySetResponse)
def get_financing_strategy_set_route(financing_strategy_set_id: str, session: DBSession) -> FinancingStrategySetResponse:
    return _to_set_response(get_financing_strategy_set(session, financing_strategy_set_id))


@router.get("/financing-strategy", response_model=list[FinancingStrategySetResponse])
def list_financing_strategy_sets_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[FinancingStrategySetResponse]:
    return [_to_set_response(item) for item in list_financing_strategy_sets(session, deal_id=deal_id)]


@router.get("/financing-strategy/records/{financing_strategy_id}", response_model=FinancingStrategyRecordResponse)
def get_financing_strategy_record_route(financing_strategy_id: str, session: DBSession) -> FinancingStrategyRecordResponse:
    return _to_record_response(get_financing_strategy_record(session, financing_strategy_id))
