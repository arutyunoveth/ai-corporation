from fastapi import APIRouter, Query, status

from src.modules.cost_model.schemas import BuildCostModelRequest, CostModelLineResponse, CostModelRecordResponse, CostModelSetResponse
from src.modules.cost_model.service import build_cost_model, get_cost_model_record, get_cost_model_set, list_cost_model_sets
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["cost-model"])


def _to_record_response(result: tuple) -> CostModelRecordResponse:
    record, lines = result
    return CostModelRecordResponse(
        cost_model_id=record.cost_model_id,
        cost_model_set_id=record.cost_model_set_id,
        base_quote_total=record.base_quote_total,
        logistics_cost=record.logistics_cost,
        buffer_cost=record.buffer_cost,
        overhead_cost=record.overhead_cost,
        total_cost=record.total_cost,
        min_viable_bid=record.min_viable_bid,
        currency_code=record.currency_code,
        created_at=record.created_at,
        updated_at=record.updated_at,
        lines=[CostModelLineResponse.model_validate(item) for item in lines],
    )


def _to_set_response(result: tuple) -> CostModelSetResponse:
    cost_model_set, records = result
    return CostModelSetResponse(
        cost_model_set_id=cost_model_set.cost_model_set_id,
        deal_id=cost_model_set.deal_id,
        quote_comparison_set_id=cost_model_set.quote_comparison_set_id,
        cost_model_status=cost_model_set.cost_model_status,
        created_at=cost_model_set.created_at,
        updated_at=cost_model_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/cost-model/build", response_model=CostModelSetResponse, status_code=status.HTTP_201_CREATED)
def build_cost_model_route(payload: BuildCostModelRequest, session: DBSession) -> CostModelSetResponse:
    cost_model_set = build_cost_model(session, payload)
    return _to_set_response(get_cost_model_set(session, cost_model_set.cost_model_set_id))


@router.get("/cost-model/{cost_model_set_id}", response_model=CostModelSetResponse)
def get_cost_model_set_route(cost_model_set_id: str, session: DBSession) -> CostModelSetResponse:
    return _to_set_response(get_cost_model_set(session, cost_model_set_id))


@router.get("/cost-model", response_model=list[CostModelSetResponse])
def list_cost_model_sets_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[CostModelSetResponse]:
    return [_to_set_response(item) for item in list_cost_model_sets(session, deal_id=deal_id)]


@router.get("/cost-model/records/{cost_model_id}", response_model=CostModelRecordResponse)
def get_cost_model_record_route(cost_model_id: str, session: DBSession) -> CostModelRecordResponse:
    return _to_record_response(get_cost_model_record(session, cost_model_id))
