from fastapi import APIRouter, Query, status

from src.modules.customer_registry.schemas import (
    CreateCustomerRequest,
    CustomerContourResponse,
    CustomerExternalRefResponse,
    CustomerProfileResponse,
    UpdateCustomerRequest,
)
from src.modules.customer_registry.service import create_customer, get_customer, list_customers, update_customer
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["customers"])


def _to_customer_response(result: tuple, *, duplicate_hint: bool = False) -> CustomerProfileResponse:
    profile, external_refs, contours = result
    return CustomerProfileResponse(
        customer_id=profile.customer_id,
        legal_name=profile.legal_name,
        inn=profile.inn,
        kpp=profile.kpp,
        customer_status=profile.customer_status,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        duplicate_hint=duplicate_hint,
        external_refs=[CustomerExternalRefResponse.model_validate(item) for item in external_refs],
        contours=[CustomerContourResponse.model_validate(item) for item in contours],
    )


@router.post("/customers", response_model=CustomerProfileResponse, status_code=status.HTTP_201_CREATED)
def create_customer_route(payload: CreateCustomerRequest, session: DBSession) -> CustomerProfileResponse:
    profile, duplicate_hint = create_customer(session, payload)
    return _to_customer_response(get_customer(session, profile.customer_id), duplicate_hint=duplicate_hint)


@router.get("/customers/{customer_id}", response_model=CustomerProfileResponse)
def get_customer_route(customer_id: str, session: DBSession) -> CustomerProfileResponse:
    return _to_customer_response(get_customer(session, customer_id))


@router.get("/customers", response_model=list[CustomerProfileResponse])
def list_customers_route(
    session: DBSession,
    q: str | None = Query(default=None),
    inn: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
) -> list[CustomerProfileResponse]:
    return [_to_customer_response(item) for item in list_customers(session, q=q, inn=inn, status=status_filter)]


@router.patch("/customers/{customer_id}", response_model=CustomerProfileResponse)
def update_customer_route(customer_id: str, payload: UpdateCustomerRequest, session: DBSession) -> CustomerProfileResponse:
    update_customer(session, customer_id, payload)
    return _to_customer_response(get_customer(session, customer_id))
