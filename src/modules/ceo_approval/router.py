from fastapi import APIRouter, Query, status

from src.modules.ceo_approval.schemas import (
    BuildCEOApprovalRequest,
    CEOApprovalConditionResponse,
    CEOApprovalRecordResponse,
    CEOApprovalSetResponse,
    RecordCEODecisionRequest,
)
from src.modules.ceo_approval.service import (
    build_ceo_approval,
    get_ceo_approval_record,
    get_ceo_approval_set,
    list_ceo_approval_sets,
    record_ceo_decision,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["ceo-approval"])


def _to_record_response(result: tuple) -> CEOApprovalRecordResponse:
    record, conditions = result
    return CEOApprovalRecordResponse(
        ceo_approval_id=record.ceo_approval_id,
        ceo_approval_set_id=record.ceo_approval_set_id,
        decision=record.decision,
        decided_by_ref=record.decided_by_ref,
        rationale=record.rationale,
        decided_at=record.decided_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        conditions=[CEOApprovalConditionResponse.model_validate(item) for item in conditions],
    )


def _to_set_response(result: tuple) -> CEOApprovalSetResponse:
    approval_set, records = result
    return CEOApprovalSetResponse(
        ceo_approval_set_id=approval_set.ceo_approval_set_id,
        deal_id=approval_set.deal_id,
        finance_memo_set_id=approval_set.finance_memo_set_id,
        integrated_risk_memo_set_id=approval_set.integrated_risk_memo_set_id,
        approval_status=approval_set.approval_status,
        created_at=approval_set.created_at,
        updated_at=approval_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/ceo-approval/build", response_model=CEOApprovalSetResponse, status_code=status.HTTP_201_CREATED)
def build_ceo_approval_route(
    payload: BuildCEOApprovalRequest,
    session: DBSession,
) -> CEOApprovalSetResponse:
    approval_set = build_ceo_approval(session, payload)
    return _to_set_response(get_ceo_approval_set(session, approval_set.ceo_approval_set_id))


@router.post("/ceo-approval/decide", response_model=CEOApprovalRecordResponse, status_code=status.HTTP_201_CREATED)
def record_ceo_decision_route(
    payload: RecordCEODecisionRequest,
    session: DBSession,
) -> CEOApprovalRecordResponse:
    record = record_ceo_decision(session, payload)
    return _to_record_response(get_ceo_approval_record(session, record.ceo_approval_id))


@router.get("/ceo-approval/{ceo_approval_set_id}", response_model=CEOApprovalSetResponse)
def get_ceo_approval_set_route(ceo_approval_set_id: str, session: DBSession) -> CEOApprovalSetResponse:
    return _to_set_response(get_ceo_approval_set(session, ceo_approval_set_id))


@router.get("/ceo-approval", response_model=list[CEOApprovalSetResponse])
def list_ceo_approval_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[CEOApprovalSetResponse]:
    return [_to_set_response(item) for item in list_ceo_approval_sets(session, deal_id=deal_id)]


@router.get("/ceo-approval/records/{ceo_approval_id}", response_model=CEOApprovalRecordResponse)
def get_ceo_approval_record_route(ceo_approval_id: str, session: DBSession) -> CEOApprovalRecordResponse:
    return _to_record_response(get_ceo_approval_record(session, ceo_approval_id))
