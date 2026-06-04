from fastapi import APIRouter, Query, status

from src.modules.purchase_orders.schemas import (
    BuildPurchaseOrderRequest,
    PurchaseOrderItemResponse,
    PurchaseOrderLinkResponse,
    PurchaseOrderRecordResponse,
    PurchaseOrderSetResponse,
)
from src.modules.purchase_orders.service import (
    build_purchase_order,
    get_purchase_order_record,
    get_purchase_order_set,
    list_purchase_order_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["purchase-orders"])


def _to_record_response(result: tuple) -> PurchaseOrderRecordResponse:
    record, items, links = result
    return PurchaseOrderRecordResponse(
        purchase_order_id=record.purchase_order_id,
        po_number=record.po_number,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[PurchaseOrderItemResponse.model_validate(item) for item in items],
        links=[PurchaseOrderLinkResponse.model_validate(item) for item in links],
    )


def _to_set_response(result: tuple) -> PurchaseOrderSetResponse:
    po_set, records = result
    return PurchaseOrderSetResponse(
        purchase_order_set_id=po_set.purchase_order_set_id,
        deal_id=po_set.deal_id,
        supplier_id=po_set.supplier_id,
        po_status=po_set.po_status,
        created_at=po_set.created_at,
        updated_at=po_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/purchase-orders/build", response_model=PurchaseOrderSetResponse, status_code=status.HTTP_201_CREATED)
def build_purchase_order_route(payload: BuildPurchaseOrderRequest, session: DBSession) -> PurchaseOrderSetResponse:
    po_set = build_purchase_order(session, payload)
    return _to_set_response(get_purchase_order_set(session, po_set.purchase_order_set_id))


@router.get("/purchase-orders/{purchase_order_set_id}", response_model=PurchaseOrderSetResponse)
def get_purchase_order_set_route(purchase_order_set_id: str, session: DBSession) -> PurchaseOrderSetResponse:
    return _to_set_response(get_purchase_order_set(session, purchase_order_set_id))


@router.get("/purchase-orders", response_model=list[PurchaseOrderSetResponse])
def list_purchase_order_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[PurchaseOrderSetResponse]:
    return [_to_set_response(item) for item in list_purchase_order_sets(session, deal_id=deal_id)]


@router.get("/purchase-orders/records/{purchase_order_id}", response_model=PurchaseOrderRecordResponse)
def get_purchase_order_record_route(purchase_order_id: str, session: DBSession) -> PurchaseOrderRecordResponse:
    return _to_record_response(get_purchase_order_record(session, purchase_order_id))
