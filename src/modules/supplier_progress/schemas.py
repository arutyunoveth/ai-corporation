from datetime import datetime

from src.shared.enums import (
    SupplierProgressEventType,
    SupplierProgressStatus,
    SupplierReadinessState,
)
from src.shared.types.common import APIModel


class BuildSupplierProgressRequest(APIModel):
    deal_id: str
    supplier_id: str


class RegisterSupplierProgressEventRequest(APIModel):
    supplier_progress_id: str
    event_type: SupplierProgressEventType = SupplierProgressEventType.STATUS_UPDATE
    summary: str
    readiness_state: SupplierReadinessState | None = None
    source_ref: str | None = None
    event_timestamp: datetime | None = None


class SupplierProgressEventResponse(APIModel):
    supplier_progress_event_id: str
    event_type: SupplierProgressEventType
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class SupplierProgressAlertResponse(APIModel):
    alert_code: str
    severity: str
    summary: str
    created_at: datetime


class SupplierProgressRecordResponse(APIModel):
    supplier_progress_id: str
    readiness_state: SupplierReadinessState
    summary_text: str
    created_at: datetime
    updated_at: datetime
    events: list[SupplierProgressEventResponse]
    alerts: list[SupplierProgressAlertResponse]


class SupplierProgressSetResponse(APIModel):
    supplier_progress_set_id: str
    deal_id: str
    supplier_id: str
    progress_status: SupplierProgressStatus
    created_at: datetime
    updated_at: datetime
    records: list[SupplierProgressRecordResponse]
