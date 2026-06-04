from fastapi import APIRouter, Query, status

from src.modules.supplier_contracts.schemas import (
    BuildSupplierContractRequest,
    SupplierContractCommentResponse,
    SupplierContractObligationResponse,
    SupplierContractRecordResponse,
    SupplierContractSetResponse,
)
from src.modules.supplier_contracts.service import (
    build_supplier_contract,
    get_supplier_contract_record,
    get_supplier_contract_set,
    list_supplier_contract_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["supplier-contracts"])


def _to_record_response(result: tuple) -> SupplierContractRecordResponse:
    record, obligations, comments = result
    return SupplierContractRecordResponse(
        supplier_contract_id=record.supplier_contract_id,
        summary_text=record.summary_text,
        contract_manifest_json=record.contract_manifest_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        obligations=[SupplierContractObligationResponse.model_validate(item) for item in obligations],
        comments=[SupplierContractCommentResponse.model_validate(item) for item in comments],
    )


def _to_set_response(result: tuple) -> SupplierContractSetResponse:
    contract_set, records = result
    return SupplierContractSetResponse(
        supplier_contract_set_id=contract_set.supplier_contract_set_id,
        deal_id=contract_set.deal_id,
        supplier_id=contract_set.supplier_id,
        contract_status=contract_set.contract_status,
        created_at=contract_set.created_at,
        updated_at=contract_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/supplier-contracts/build", response_model=SupplierContractSetResponse, status_code=status.HTTP_201_CREATED)
def build_supplier_contract_route(payload: BuildSupplierContractRequest, session: DBSession) -> SupplierContractSetResponse:
    contract_set = build_supplier_contract(session, payload)
    return _to_set_response(get_supplier_contract_set(session, contract_set.supplier_contract_set_id))


@router.get("/supplier-contracts/{supplier_contract_set_id}", response_model=SupplierContractSetResponse)
def get_supplier_contract_set_route(
    supplier_contract_set_id: str,
    session: DBSession,
) -> SupplierContractSetResponse:
    return _to_set_response(get_supplier_contract_set(session, supplier_contract_set_id))


@router.get("/supplier-contracts", response_model=list[SupplierContractSetResponse])
def list_supplier_contract_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SupplierContractSetResponse]:
    return [_to_set_response(item) for item in list_supplier_contract_sets(session, deal_id=deal_id)]


@router.get("/supplier-contracts/records/{supplier_contract_id}", response_model=SupplierContractRecordResponse)
def get_supplier_contract_record_route(
    supplier_contract_id: str,
    session: DBSession,
) -> SupplierContractRecordResponse:
    return _to_record_response(get_supplier_contract_record(session, supplier_contract_id))
