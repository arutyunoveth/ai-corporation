from fastapi import APIRouter, Query, status

from src.modules.supplier_search.schemas import BuildSupplierShortlistRequest, SupplierShortlistResponse, SupplierShortlistRowResponse
from src.modules.supplier_search.service import build_supplier_shortlist, get_supplier_shortlist, list_supplier_shortlists
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["supplier-search"])


def _to_response(result: tuple) -> SupplierShortlistResponse:
    shortlist, rows = result
    return SupplierShortlistResponse(
        supplier_shortlist_id=shortlist.supplier_shortlist_id,
        deal_id=shortlist.deal_id,
        intake_id=shortlist.intake_id,
        document_set_id=shortlist.document_set_id,
        tender_summary_id=shortlist.tender_summary_id,
        shortlist_status=shortlist.shortlist_status,
        created_at=shortlist.created_at,
        updated_at=shortlist.updated_at,
        rows=[SupplierShortlistRowResponse.model_validate(item) for item in rows],
    )


@router.post("/supplier-search/build", response_model=SupplierShortlistResponse, status_code=status.HTTP_201_CREATED)
def build_supplier_shortlist_route(payload: BuildSupplierShortlistRequest, session: DBSession) -> SupplierShortlistResponse:
    shortlist = build_supplier_shortlist(session, payload)
    return _to_response(get_supplier_shortlist(session, shortlist.supplier_shortlist_id))


@router.get("/supplier-search/{supplier_shortlist_id}", response_model=SupplierShortlistResponse)
def get_supplier_shortlist_route(supplier_shortlist_id: str, session: DBSession) -> SupplierShortlistResponse:
    return _to_response(get_supplier_shortlist(session, supplier_shortlist_id))


@router.get("/supplier-search", response_model=list[SupplierShortlistResponse])
def list_supplier_shortlists_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[SupplierShortlistResponse]:
    return [_to_response(item) for item in list_supplier_shortlists(session, deal_id=deal_id)]
