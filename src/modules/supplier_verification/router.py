from fastapi import APIRouter, Query, status

from src.modules.supplier_verification.schemas import (
    BuildSupplierVerificationRequest,
    SupplierVerificationFlagResponse,
    SupplierVerificationRecordResponse,
    SupplierVerificationSetResponse,
)
from src.modules.supplier_verification.service import (
    build_supplier_verification,
    get_supplier_verification_record,
    get_supplier_verification_set,
    list_supplier_verification_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["supplier-verification"])


def _to_record_response(result: tuple) -> SupplierVerificationRecordResponse:
    record, flags = result
    return SupplierVerificationRecordResponse(
        supplier_verification_id=record.supplier_verification_id,
        supplier_verification_set_id=record.supplier_verification_set_id,
        supplier_id=record.supplier_id,
        verification_result=record.verification_result,
        confidence_score=record.confidence_score,
        notes=record.notes,
        created_at=record.created_at,
        updated_at=record.updated_at,
        flags=[SupplierVerificationFlagResponse.model_validate(item) for item in flags],
    )


def _to_set_response(result: tuple) -> SupplierVerificationSetResponse:
    verification_set, records = result
    return SupplierVerificationSetResponse(
        supplier_verification_set_id=verification_set.supplier_verification_set_id,
        deal_id=verification_set.deal_id,
        supplier_shortlist_id=verification_set.supplier_shortlist_id,
        verification_status=verification_set.verification_status,
        created_at=verification_set.created_at,
        updated_at=verification_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/supplier-verification/build", response_model=SupplierVerificationSetResponse, status_code=status.HTTP_201_CREATED)
def build_supplier_verification_route(
    payload: BuildSupplierVerificationRequest, session: DBSession
) -> SupplierVerificationSetResponse:
    verification_set = build_supplier_verification(session, payload)
    return _to_set_response(get_supplier_verification_set(session, verification_set.supplier_verification_set_id))


@router.get("/supplier-verification/{supplier_verification_set_id}", response_model=SupplierVerificationSetResponse)
def get_supplier_verification_set_route(
    supplier_verification_set_id: str, session: DBSession
) -> SupplierVerificationSetResponse:
    return _to_set_response(get_supplier_verification_set(session, supplier_verification_set_id))


@router.get("/supplier-verification", response_model=list[SupplierVerificationSetResponse])
def list_supplier_verification_sets_route(
    session: DBSession, deal_id: str | None = Query(default=None)
) -> list[SupplierVerificationSetResponse]:
    return [_to_set_response(item) for item in list_supplier_verification_sets(session, deal_id=deal_id)]


@router.get("/supplier-verification/records/{supplier_verification_id}", response_model=SupplierVerificationRecordResponse)
def get_supplier_verification_record_route(
    supplier_verification_id: str, session: DBSession
) -> SupplierVerificationRecordResponse:
    return _to_record_response(get_supplier_verification_record(session, supplier_verification_id))
