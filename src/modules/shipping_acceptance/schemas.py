from datetime import datetime

from src.shared.enums import ShippingAcceptanceState, ShippingAcceptanceStatus
from src.shared.types.common import APIModel


class BuildShippingAcceptanceRequest(APIModel):
    deal_id: str
    execution_command_set_id: str
    shipment_ref: str | None = None
    acceptance_ref: str | None = None


class RegisterShippingAcceptanceEventRequest(APIModel):
    shipping_acceptance_id: str
    summary: str
    event_timestamp: datetime | None = None
    source_ref: str | None = None
    current_state: ShippingAcceptanceState | None = None
    shipment_ref: str | None = None
    acceptance_ref: str | None = None


class ShippingAcceptanceEventResponse(APIModel):
    shipping_acceptance_event_id: str
    shipping_acceptance_id: str
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class ShippingAcceptanceRecordResponse(APIModel):
    shipping_acceptance_id: str
    shipping_acceptance_set_id: str
    shipment_ref: str | None
    acceptance_ref: str | None
    current_state: ShippingAcceptanceState
    created_at: datetime
    updated_at: datetime
    events: list[ShippingAcceptanceEventResponse]


class ShippingAcceptanceSetResponse(APIModel):
    shipping_acceptance_set_id: str
    deal_id: str
    execution_command_set_id: str
    shipping_status: ShippingAcceptanceStatus
    created_at: datetime
    updated_at: datetime
    records: list[ShippingAcceptanceRecordResponse]
