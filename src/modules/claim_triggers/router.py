from fastapi import APIRouter, Query, status

from src.modules.claim_triggers.schemas import (
    BuildClaimTriggerRequest,
    ClaimTriggerFlagResponse,
    ClaimTriggerLinkResponse,
    ClaimTriggerRecordResponse,
    ClaimTriggerSetResponse,
)
from src.modules.claim_triggers.service import (
    build_claim_trigger,
    get_claim_trigger_record,
    get_claim_trigger_set,
    list_claim_trigger_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["claim-triggers"])


def _to_record_response(result: tuple) -> ClaimTriggerRecordResponse:
    record, flags, links = result
    return ClaimTriggerRecordResponse(
        claim_trigger_id=record.claim_trigger_id,
        summary_text=record.summary_text,
        trigger_reason=record.trigger_reason,
        created_at=record.created_at,
        updated_at=record.updated_at,
        flags=[ClaimTriggerFlagResponse.model_validate(item) for item in flags],
        links=[ClaimTriggerLinkResponse.model_validate(item) for item in links],
    )


def _to_set_response(result: tuple) -> ClaimTriggerSetResponse:
    trigger_set, records = result
    return ClaimTriggerSetResponse(
        claim_trigger_set_id=trigger_set.claim_trigger_set_id,
        deal_id=trigger_set.deal_id,
        trigger_status=trigger_set.trigger_status,
        created_at=trigger_set.created_at,
        updated_at=trigger_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/claim-triggers/build", response_model=ClaimTriggerSetResponse, status_code=status.HTTP_201_CREATED)
def build_claim_trigger_route(payload: BuildClaimTriggerRequest, session: DBSession) -> ClaimTriggerSetResponse:
    trigger_set = build_claim_trigger(session, payload)
    return _to_set_response(get_claim_trigger_set(session, trigger_set.claim_trigger_set_id))


@router.get("/claim-triggers/{claim_trigger_set_id}", response_model=ClaimTriggerSetResponse)
def get_claim_trigger_set_route(claim_trigger_set_id: str, session: DBSession) -> ClaimTriggerSetResponse:
    return _to_set_response(get_claim_trigger_set(session, claim_trigger_set_id))


@router.get("/claim-triggers", response_model=list[ClaimTriggerSetResponse])
def list_claim_trigger_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ClaimTriggerSetResponse]:
    return [_to_set_response(item) for item in list_claim_trigger_sets(session, deal_id=deal_id)]


@router.get("/claim-triggers/records/{claim_trigger_id}", response_model=ClaimTriggerRecordResponse)
def get_claim_trigger_record_route(claim_trigger_id: str, session: DBSession) -> ClaimTriggerRecordResponse:
    return _to_record_response(get_claim_trigger_record(session, claim_trigger_id))
