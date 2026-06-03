from fastapi import APIRouter, Query, status

from src.modules.supplier_registry.schemas import (
    CreateSupplierContactRequest,
    CreateSupplierRequest,
    CreateSupplierTagRequest,
    SupplierContactResponse,
    SupplierExternalRefResponse,
    SupplierProfileResponse,
    SupplierTagResponse,
    UpdateSupplierRequest,
)
from src.modules.supplier_registry.service import (
    add_supplier_contact,
    add_supplier_tag,
    create_supplier,
    get_supplier,
    list_suppliers,
    update_supplier,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["suppliers"])


def _to_supplier_response(result: tuple, *, duplicate_hint: bool = False) -> SupplierProfileResponse:
    supplier, external_refs, contacts, tags = result
    return SupplierProfileResponse(
        supplier_id=supplier.supplier_id,
        legal_name=supplier.legal_name,
        display_name=supplier.display_name,
        inn=supplier.inn,
        country_code=supplier.country_code,
        status=supplier.status,
        notes=supplier.notes,
        created_at=supplier.created_at,
        updated_at=supplier.updated_at,
        duplicate_hint=duplicate_hint,
        external_refs=[SupplierExternalRefResponse.model_validate(item) for item in external_refs],
        contacts=[SupplierContactResponse.model_validate(item) for item in contacts],
        tags=[SupplierTagResponse.model_validate(item) for item in tags],
    )


@router.post("/suppliers", response_model=SupplierProfileResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_route(payload: CreateSupplierRequest, session: DBSession) -> SupplierProfileResponse:
    supplier, duplicate_hint = create_supplier(session, payload)
    return _to_supplier_response(get_supplier(session, supplier.supplier_id), duplicate_hint=duplicate_hint)


@router.get("/suppliers/{supplier_id}", response_model=SupplierProfileResponse)
def get_supplier_route(supplier_id: str, session: DBSession) -> SupplierProfileResponse:
    return _to_supplier_response(get_supplier(session, supplier_id))


@router.get("/suppliers", response_model=list[SupplierProfileResponse])
def list_suppliers_route(
    session: DBSession,
    q: str | None = Query(default=None),
    inn: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[SupplierProfileResponse]:
    return [_to_supplier_response(item) for item in list_suppliers(session, q=q, inn=inn, status=status_filter)]


@router.patch("/suppliers/{supplier_id}", response_model=SupplierProfileResponse)
def update_supplier_route(supplier_id: str, payload: UpdateSupplierRequest, session: DBSession) -> SupplierProfileResponse:
    update_supplier(session, supplier_id, payload)
    return _to_supplier_response(get_supplier(session, supplier_id))


@router.post("/suppliers/{supplier_id}/contacts", response_model=SupplierContactResponse, status_code=status.HTTP_201_CREATED)
def add_supplier_contact_route(
    supplier_id: str,
    payload: CreateSupplierContactRequest,
    session: DBSession,
) -> SupplierContactResponse:
    return SupplierContactResponse.model_validate(add_supplier_contact(session, supplier_id, payload))


@router.post("/suppliers/{supplier_id}/tags", response_model=SupplierTagResponse, status_code=status.HTTP_201_CREATED)
def add_supplier_tag_route(
    supplier_id: str,
    payload: CreateSupplierTagRequest,
    session: DBSession,
) -> SupplierTagResponse:
    return SupplierTagResponse.model_validate(add_supplier_tag(session, supplier_id, payload))
