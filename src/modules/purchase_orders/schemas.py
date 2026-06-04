from datetime import datetime

from src.shared.enums import PurchaseOrderStatus
from src.shared.types.common import APIModel


class BuildPurchaseOrderRequest(APIModel):
    deal_id: str
    supplier_id: str


class PurchaseOrderItemResponse(APIModel):
    item_code: str
    item_description: str
    quantity: int
    created_at: datetime


class PurchaseOrderLinkResponse(APIModel):
    source_ref: str
    created_at: datetime


class PurchaseOrderRecordResponse(APIModel):
    purchase_order_id: str
    po_number: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    items: list[PurchaseOrderItemResponse]
    links: list[PurchaseOrderLinkResponse]


class PurchaseOrderSetResponse(APIModel):
    purchase_order_set_id: str
    deal_id: str
    supplier_id: str
    po_status: PurchaseOrderStatus
    created_at: datetime
    updated_at: datetime
    records: list[PurchaseOrderRecordResponse]
