from fastapi import APIRouter, Query, status

from src.modules.integrated_risk_memo.schemas import (
    BuildIntegratedRiskMemoRequest,
    IntegratedRiskItemResponse,
    IntegratedRiskMemoRecordResponse,
    IntegratedRiskMemoSetResponse,
)
from src.modules.integrated_risk_memo.service import (
    build_integrated_risk_memo,
    get_integrated_risk_memo_record,
    get_integrated_risk_memo_set,
    list_integrated_risk_memo_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["integrated-risk-memo"])


def _to_record_response(result: tuple) -> IntegratedRiskMemoRecordResponse:
    record, items = result
    return IntegratedRiskMemoRecordResponse(
        integrated_risk_memo_id=record.integrated_risk_memo_id,
        integrated_risk_memo_set_id=record.integrated_risk_memo_set_id,
        summary_text=record.summary_text,
        structured_summary_json=record.structured_summary_json,
        recommendation=record.recommendation,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[IntegratedRiskItemResponse.model_validate(item) for item in items],
    )


def _to_set_response(result: tuple) -> IntegratedRiskMemoSetResponse:
    memo_set, records = result
    return IntegratedRiskMemoSetResponse(
        integrated_risk_memo_set_id=memo_set.integrated_risk_memo_set_id,
        deal_id=memo_set.deal_id,
        initial_tech_risk_flag_set_id=memo_set.initial_tech_risk_flag_set_id,
        supplier_verification_set_id=memo_set.supplier_verification_set_id,
        quote_comparison_set_id=memo_set.quote_comparison_set_id,
        finance_memo_set_id=memo_set.finance_memo_set_id,
        contract_risk_set_id=memo_set.contract_risk_set_id,
        memo_status=memo_set.memo_status,
        created_at=memo_set.created_at,
        updated_at=memo_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post(
    "/integrated-risk-memo/build",
    response_model=IntegratedRiskMemoSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def build_integrated_risk_memo_route(
    payload: BuildIntegratedRiskMemoRequest,
    session: DBSession,
) -> IntegratedRiskMemoSetResponse:
    memo_set = build_integrated_risk_memo(session, payload)
    return _to_set_response(get_integrated_risk_memo_set(session, memo_set.integrated_risk_memo_set_id))


@router.get("/integrated-risk-memo/{integrated_risk_memo_set_id}", response_model=IntegratedRiskMemoSetResponse)
def get_integrated_risk_memo_set_route(
    integrated_risk_memo_set_id: str,
    session: DBSession,
) -> IntegratedRiskMemoSetResponse:
    return _to_set_response(get_integrated_risk_memo_set(session, integrated_risk_memo_set_id))


@router.get("/integrated-risk-memo", response_model=list[IntegratedRiskMemoSetResponse])
def list_integrated_risk_memo_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[IntegratedRiskMemoSetResponse]:
    return [_to_set_response(item) for item in list_integrated_risk_memo_sets(session, deal_id=deal_id)]


@router.get(
    "/integrated-risk-memo/records/{integrated_risk_memo_id}",
    response_model=IntegratedRiskMemoRecordResponse,
)
def get_integrated_risk_memo_record_route(
    integrated_risk_memo_id: str,
    session: DBSession,
) -> IntegratedRiskMemoRecordResponse:
    return _to_record_response(get_integrated_risk_memo_record(session, integrated_risk_memo_id))
