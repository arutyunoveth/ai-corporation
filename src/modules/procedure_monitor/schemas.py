from datetime import datetime

from pydantic import Field

from src.shared.enums import ProcedureMonitorEventType, ProcedureStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildProcedureMonitorRequest(APIModel):
    deal_id: str


class RegisterProcedureMonitorEventRequest(APIModel):
    procedure_monitor_id: str
    event_type: ProcedureMonitorEventType
    event_timestamp: datetime | None = None
    summary: str
    source_ref: str | None = None
    current_stage: str | None = None


class ProcedureMonitorEventResponse(APIModel):
    procedure_event_id: str
    procedure_monitor_id: str
    event_type: ProcedureMonitorEventType
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class ProcedureMonitorAlertResponse(APIModel):
    alert_code: str
    severity: RiskSeverity
    summary: str
    created_at: datetime


class ProcedureMonitorRecordResponse(APIModel):
    procedure_monitor_id: str
    procedure_monitor_set_id: str
    current_stage: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    events: list[ProcedureMonitorEventResponse] = Field(default_factory=list)
    alerts: list[ProcedureMonitorAlertResponse] = Field(default_factory=list)


class ProcedureMonitorSetResponse(APIModel):
    procedure_monitor_set_id: str
    deal_id: str
    procedure_status: ProcedureStatus
    created_at: datetime
    updated_at: datetime
    records: list[ProcedureMonitorRecordResponse] = Field(default_factory=list)
