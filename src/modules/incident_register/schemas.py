from datetime import datetime

from src.shared.enums import (
    IncidentRegisterEventType,
    IncidentRegisterStatus,
    IncidentRegisterType,
    RiskSeverity,
)
from src.shared.types.common import APIModel


class BuildIncidentRegisterRequest(APIModel):
    deal_id: str


class RegisterIncidentRegisterEventRequest(APIModel):
    incident_register_id: str
    event_type: IncidentRegisterEventType
    summary: str
    event_timestamp: datetime | None = None
    source_ref: str | None = None
    severity: RiskSeverity | None = None
    incident_status: IncidentRegisterStatus | None = None
    flag_code: str | None = None


class IncidentRegisterEventResponse(APIModel):
    incident_register_event_id: str
    incident_register_id: str
    event_type: IncidentRegisterEventType
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class IncidentRegisterFlagResponse(APIModel):
    flag_code: str
    severity: RiskSeverity
    summary: str
    created_at: datetime


class IncidentRegisterRecordResponse(APIModel):
    incident_register_id: str
    incident_type: IncidentRegisterType
    severity: RiskSeverity
    summary_text: str
    created_at: datetime
    updated_at: datetime
    events: list[IncidentRegisterEventResponse]
    flags: list[IncidentRegisterFlagResponse]


class IncidentRegisterSetResponse(APIModel):
    incident_register_set_id: str
    deal_id: str
    incident_status: IncidentRegisterStatus
    created_at: datetime
    updated_at: datetime
    records: list[IncidentRegisterRecordResponse]
