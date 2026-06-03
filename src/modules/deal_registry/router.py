from datetime import datetime

from fastapi import APIRouter, Query, status

from src.modules.deal_registry.schemas import CreateDealRequest, CreateDealResponse, DealResponse, UpdateDealRequest
from src.modules.deal_registry.service import create_deal, get_deal, list_deals, update_deal
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["deals"])


@router.post("/deals", response_model=CreateDealResponse, status_code=status.HTTP_201_CREATED)
def create_deal_route(payload: CreateDealRequest, session: DBSession) -> CreateDealResponse:
    deal = create_deal(session, payload)
    return CreateDealResponse(deal_id=deal.deal_id, current_status=deal.current_status, created_at=deal.created_at)


@router.get("/deals", response_model=list[DealResponse])
def list_deals_route(
    session: DBSession,
    status: str | None = None,
    date_from: datetime | None = Query(default=None),
    date_to: datetime | None = Query(default=None),
    procurement_number: str | None = None,
    customer_name: str | None = None,
) -> list[DealResponse]:
    return [DealResponse.model_validate(deal) for deal in list_deals(
        session,
        status=status,
        date_from=date_from,
        date_to=date_to,
        procurement_number=procurement_number,
        customer_name=customer_name,
    )]


@router.get("/deals/{deal_id}", response_model=DealResponse)
def get_deal_route(deal_id: str, session: DBSession) -> DealResponse:
    return DealResponse.model_validate(get_deal(session, deal_id))


@router.patch("/deals/{deal_id}", response_model=DealResponse)
def update_deal_route(deal_id: str, payload: UpdateDealRequest, session: DBSession) -> DealResponse:
    return DealResponse.model_validate(update_deal(session, deal_id, payload))

