from datetime import datetime

from src.shared.enums import EscalationLevel, EscalationStatus, IncidentStatus, IncidentType, RiskSeverity
from src.shared.types.common import APIModel


class BuildIncidentSetRequest(APIModel):
    deal_id: str
    execution_command_set_id: str


class RegisterIncidentRequest(APIModel):
    incident_set_id: str
    incident_type: IncidentType
    severity: RiskSeverity
    summary: str
    source_ref: str | None = None


class EscalateIncidentRequest(APIModel):
    incident_id: str
    escalation_level: EscalationLevel
    escalation_status: EscalationStatus = EscalationStatus.OPEN
    notes: str | None = None
    incident_status: IncidentStatus | None = None


class EscalationRecordResponse(APIModel):
    escalation_id: str
    incident_id: str
    escalation_level: EscalationLevel
    escalation_status: EscalationStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class IncidentRecordResponse(APIModel):
    incident_id: str
    incident_set_id: str
    incident_type: IncidentType
    severity: RiskSeverity
    summary: str
    source_ref: str | None
    created_at: datetime
    updated_at: datetime
    escalations: list[EscalationRecordResponse]


class IncidentSetResponse(APIModel):
    incident_set_id: str
    deal_id: str
    execution_command_set_id: str
    incident_status: IncidentStatus
    created_at: datetime
    updated_at: datetime
    records: list[IncidentRecordResponse]
