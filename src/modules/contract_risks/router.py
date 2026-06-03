from fastapi import APIRouter, Query, status

from src.modules.contract_risks.schemas import (
    BuildContractRiskRequest,
    ContractRiskFlagResponse,
    ContractRiskRecordResponse,
    ContractRiskSetResponse,
)
from src.modules.contract_risks.service import (
    build_contract_risks,
    get_contract_risk_record,
    get_contract_risk_set,
    list_contract_risk_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["contract-risks"])


def _to_record_response(result: tuple) -> ContractRiskRecordResponse:
    record, flags = result
    return ContractRiskRecordResponse(
        contract_risk_id=record.contract_risk_id,
        contract_risk_set_id=record.contract_risk_set_id,
        source_artifact_ref=record.source_artifact_ref,
        clause_type=record.clause_type,
        summary=record.summary,
        severity=record.severity,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        flags=[ContractRiskFlagResponse.model_validate(item) for item in flags],
    )


def _to_set_response(result: tuple) -> ContractRiskSetResponse:
    risk_set, records = result
    return ContractRiskSetResponse(
        contract_risk_set_id=risk_set.contract_risk_set_id,
        deal_id=risk_set.deal_id,
        document_set_id=risk_set.document_set_id,
        risk_status=risk_set.risk_status,
        created_at=risk_set.created_at,
        updated_at=risk_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/contract-risks/build", response_model=ContractRiskSetResponse, status_code=status.HTTP_201_CREATED)
def build_contract_risks_route(
    payload: BuildContractRiskRequest,
    session: DBSession,
) -> ContractRiskSetResponse:
    risk_set = build_contract_risks(session, payload)
    return _to_set_response(get_contract_risk_set(session, risk_set.contract_risk_set_id))


@router.get("/contract-risks/{contract_risk_set_id}", response_model=ContractRiskSetResponse)
def get_contract_risk_set_route(contract_risk_set_id: str, session: DBSession) -> ContractRiskSetResponse:
    return _to_set_response(get_contract_risk_set(session, contract_risk_set_id))


@router.get("/contract-risks", response_model=list[ContractRiskSetResponse])
def list_contract_risk_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ContractRiskSetResponse]:
    return [_to_set_response(item) for item in list_contract_risk_sets(session, deal_id=deal_id)]


@router.get("/contract-risks/records/{contract_risk_id}", response_model=ContractRiskRecordResponse)
def get_contract_risk_record_route(contract_risk_id: str, session: DBSession) -> ContractRiskRecordResponse:
    return _to_record_response(get_contract_risk_record(session, contract_risk_id))
