from datetime import datetime

from src.shared.enums import CollectionState, PaymentCollectionStatus
from src.shared.types.common import APIModel


class BuildPaymentCollectionRequest(APIModel):
    deal_id: str
    execution_command_set_id: str
    invoice_ref: str | None = None
    expected_amount: float | None = None
    collected_amount: float | None = None
    currency_code: str | None = None


class RegisterPaymentCollectionEventRequest(APIModel):
    payment_collection_id: str
    summary: str
    event_timestamp: datetime | None = None
    source_ref: str | None = None
    collection_state: CollectionState | None = None
    invoice_ref: str | None = None
    collected_amount: float | None = None


class PaymentCollectionEventResponse(APIModel):
    payment_collection_event_id: str
    payment_collection_id: str
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class PaymentCollectionRecordResponse(APIModel):
    payment_collection_id: str
    payment_collection_set_id: str
    invoice_ref: str | None
    expected_amount: float
    collected_amount: float
    currency_code: str
    collection_state: CollectionState
    created_at: datetime
    updated_at: datetime
    events: list[PaymentCollectionEventResponse]


class PaymentCollectionSetResponse(APIModel):
    payment_collection_set_id: str
    deal_id: str
    execution_command_set_id: str
    collection_status: PaymentCollectionStatus
    created_at: datetime
    updated_at: datetime
    records: list[PaymentCollectionRecordResponse]
