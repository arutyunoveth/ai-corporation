from datetime import datetime

from src.shared.enums import LogisticsEventType, LogisticsStatus
from src.shared.types.common import APIModel


class BuildLogisticsTrackingRequest(APIModel):
    deal_id: str


class RegisterLogisticsTrackingEventRequest(APIModel):
    logistics_tracking_id: str
    event_type: LogisticsEventType
    summary: str
    event_timestamp: datetime | None = None
    source_ref: str | None = None
    eta_at: datetime | None = None
    logistics_status: LogisticsStatus | None = None


class LogisticsTrackingEventResponse(APIModel):
    logistics_tracking_event_id: str
    logistics_tracking_id: str
    event_type: LogisticsEventType
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class LogisticsTrackingLinkResponse(APIModel):
    source_ref: str
    created_at: datetime


class LogisticsTrackingRecordResponse(APIModel):
    logistics_tracking_id: str
    eta_at: datetime | None
    summary_text: str
    created_at: datetime
    updated_at: datetime
    events: list[LogisticsTrackingEventResponse]
    links: list[LogisticsTrackingLinkResponse]


class LogisticsTrackingSetResponse(APIModel):
    logistics_tracking_set_id: str
    deal_id: str
    logistics_status: LogisticsStatus
    created_at: datetime
    updated_at: datetime
    records: list[LogisticsTrackingRecordResponse]
