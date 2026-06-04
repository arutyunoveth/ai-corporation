from fastapi import APIRouter, Query, status

from src.modules.contract_negotiation.schemas import (
    BuildContractNegotiationRequest,
    ContractNegotiationCommentResponse,
    ContractNegotiationIssueResponse,
    ContractNegotiationRecordResponse,
    ContractNegotiationSetResponse,
)
from src.modules.contract_negotiation.service import (
    build_contract_negotiation,
    get_contract_negotiation_record,
    get_contract_negotiation_set,
    list_contract_negotiation_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["contract-negotiation"])


def _to_record_response(result: tuple) -> ContractNegotiationRecordResponse:
    record, issues, comments = result
    return ContractNegotiationRecordResponse(
        contract_negotiation_id=record.contract_negotiation_id,
        contract_negotiation_set_id=record.contract_negotiation_set_id,
        summary_text=record.summary_text,
        negotiation_pack_manifest_json=record.negotiation_pack_manifest_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        issues=[ContractNegotiationIssueResponse.model_validate(item) for item in issues],
        comments=[ContractNegotiationCommentResponse.model_validate(item) for item in comments],
    )


def _to_set_response(result: tuple) -> ContractNegotiationSetResponse:
    negotiation_set, records = result
    return ContractNegotiationSetResponse(
        contract_negotiation_set_id=negotiation_set.contract_negotiation_set_id,
        deal_id=negotiation_set.deal_id,
        negotiation_status=negotiation_set.negotiation_status,
        created_at=negotiation_set.created_at,
        updated_at=negotiation_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/contract-negotiation/build", response_model=ContractNegotiationSetResponse, status_code=status.HTTP_201_CREATED)
def build_contract_negotiation_route(
    payload: BuildContractNegotiationRequest,
    session: DBSession,
) -> ContractNegotiationSetResponse:
    negotiation_set = build_contract_negotiation(session, payload)
    return _to_set_response(get_contract_negotiation_set(session, negotiation_set.contract_negotiation_set_id))


@router.get("/contract-negotiation/{contract_negotiation_set_id}", response_model=ContractNegotiationSetResponse)
def get_contract_negotiation_set_route(
    contract_negotiation_set_id: str,
    session: DBSession,
) -> ContractNegotiationSetResponse:
    return _to_set_response(get_contract_negotiation_set(session, contract_negotiation_set_id))


@router.get("/contract-negotiation", response_model=list[ContractNegotiationSetResponse])
def list_contract_negotiation_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ContractNegotiationSetResponse]:
    return [_to_set_response(item) for item in list_contract_negotiation_sets(session, deal_id=deal_id)]


@router.get("/contract-negotiation/records/{contract_negotiation_id}", response_model=ContractNegotiationRecordResponse)
def get_contract_negotiation_record_route(
    contract_negotiation_id: str,
    session: DBSession,
) -> ContractNegotiationRecordResponse:
    return _to_record_response(get_contract_negotiation_record(session, contract_negotiation_id))
