from datetime import datetime

from src.shared.enums import PaymentTrackingEventType, PaymentTrackingStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildPaymentTrackingRequest(APIModel):
    deal_id: str


class RegisterPaymentTrackingEventRequest(APIModel):
    payment_tracking_id: str
    event_type: PaymentTrackingEventType
    summary: str
    event_timestamp: datetime | None = None
    source_ref: str | None = None
    expected_amount: float | None = None
    paid_amount: float | None = None
    overdue_days: int | None = None
    payment_status: PaymentTrackingStatus | None = None


class PaymentTrackingEventResponse(APIModel):
    payment_tracking_event_id: str
    payment_tracking_id: str
    event_type: PaymentTrackingEventType
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class PaymentTrackingAlertResponse(APIModel):
    alert_code: str
    severity: RiskSeverity
    summary: str
    created_at: datetime


class PaymentTrackingRecordResponse(APIModel):
    payment_tracking_id: str
    expected_amount: float
    paid_amount: float
    overdue_days: int
    summary_text: str
    created_at: datetime
    updated_at: datetime
    events: list[PaymentTrackingEventResponse]
    alerts: list[PaymentTrackingAlertResponse]


class PaymentTrackingSetResponse(APIModel):
    payment_tracking_set_id: str
    deal_id: str
    payment_status: PaymentTrackingStatus
    created_at: datetime
    updated_at: datetime
    records: list[PaymentTrackingRecordResponse]
