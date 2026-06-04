from fastapi import APIRouter, Query, status

from src.modules.supplier_ratings.schemas import (
    BuildSupplierRatingUpdateRequest,
    SupplierRatingFactorResponse,
    SupplierRatingUpdateRecordResponse,
    SupplierRatingUpdateSetResponse,
)
from src.modules.supplier_ratings.service import (
    build_supplier_rating_update,
    get_supplier_rating_update_record,
    get_supplier_rating_update_set,
    list_supplier_rating_update_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["supplier-ratings"])


def _to_record_response(result: tuple) -> SupplierRatingUpdateRecordResponse:
    record, factors = result
    return SupplierRatingUpdateRecordResponse(
        supplier_rating_update_id=record.supplier_rating_update_id,
        prior_rating_value=record.prior_rating_value,
        updated_rating_value=record.updated_rating_value,
        rating_band=record.rating_band,
        rationale_text=record.rationale_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        factors=[SupplierRatingFactorResponse.model_validate(item) for item in factors],
    )


def _to_set_response(result: tuple) -> SupplierRatingUpdateSetResponse:
    rating_set, records = result
    return SupplierRatingUpdateSetResponse(
        supplier_rating_update_set_id=rating_set.supplier_rating_update_set_id,
        deal_id=rating_set.deal_id,
        supplier_id=rating_set.supplier_id,
        supplier_contract_set_id=rating_set.supplier_contract_set_id,
        postmortem_set_id=rating_set.postmortem_set_id,
        rating_status=rating_set.rating_status,
        created_at=rating_set.created_at,
        updated_at=rating_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/supplier-ratings/build", response_model=SupplierRatingUpdateSetResponse, status_code=status.HTTP_201_CREATED)
def build_supplier_rating_update_route(
    payload: BuildSupplierRatingUpdateRequest,
    session: DBSession,
) -> SupplierRatingUpdateSetResponse:
    rating_set = build_supplier_rating_update(session, payload)
    return _to_set_response(get_supplier_rating_update_set(session, rating_set.supplier_rating_update_set_id))


@router.get("/supplier-ratings/{supplier_rating_update_set_id}", response_model=SupplierRatingUpdateSetResponse)
def get_supplier_rating_update_set_route(
    supplier_rating_update_set_id: str,
    session: DBSession,
) -> SupplierRatingUpdateSetResponse:
    return _to_set_response(get_supplier_rating_update_set(session, supplier_rating_update_set_id))


@router.get("/supplier-ratings", response_model=list[SupplierRatingUpdateSetResponse])
def list_supplier_rating_update_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SupplierRatingUpdateSetResponse]:
    return [_to_set_response(item) for item in list_supplier_rating_update_sets(session, deal_id=deal_id)]


@router.get("/supplier-ratings/records/{supplier_rating_update_id}", response_model=SupplierRatingUpdateRecordResponse)
def get_supplier_rating_update_record_route(
    supplier_rating_update_id: str,
    session: DBSession,
) -> SupplierRatingUpdateRecordResponse:
    return _to_record_response(get_supplier_rating_update_record(session, supplier_rating_update_id))
