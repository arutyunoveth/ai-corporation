from datetime import datetime

from src.shared.enums import SupplierFulfillmentState, SupplierFulfillmentStatus
from src.shared.types.common import APIModel


class BuildSupplierFulfillmentRequest(APIModel):
    deal_id: str
    execution_command_set_id: str


class RegisterSupplierFulfillmentEventRequest(APIModel):
    supplier_fulfillment_id: str
    summary: str
    event_timestamp: datetime | None = None
    source_ref: str | None = None
    fulfillment_state: SupplierFulfillmentState | None = None


class SupplierFulfillmentEventResponse(APIModel):
    supplier_fulfillment_event_id: str
    supplier_fulfillment_id: str
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class SupplierFulfillmentRecordResponse(APIModel):
    supplier_fulfillment_id: str
    supplier_fulfillment_set_id: str
    supplier_id: str
    fulfillment_state: SupplierFulfillmentState
    summary_text: str
    created_at: datetime
    updated_at: datetime
    events: list[SupplierFulfillmentEventResponse]


class SupplierFulfillmentSetResponse(APIModel):
    supplier_fulfillment_set_id: str
    deal_id: str
    execution_command_set_id: str
    fulfillment_status: SupplierFulfillmentStatus
    created_at: datetime
    updated_at: datetime
    records: list[SupplierFulfillmentRecordResponse]
