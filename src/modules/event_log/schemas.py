from datetime import datetime

from src.shared.enums import DecisionByType, EventSeverity
from src.shared.types.common import APIModel


class AppendEventRequest(APIModel):
    deal_id: str | None = None
    event_code: str
    source_module_id: str | None = None
    source_agent_code: str | None = None
    severity: EventSeverity
    payload_json: dict | None = None


class AppendDecisionRequest(APIModel):
    deal_id: str
    decision_code: str
    decided_by_type: DecisionByType
    decided_by_ref: str | None = None
    rationale: str | None = None
    payload_json: dict | None = None


class EventResponse(APIModel):
    event_id: str
    deal_id: str | None
    event_code: str
    source_module_id: str | None
    source_agent_code: str | None
    severity: EventSeverity
    payload_json: dict | None
    created_at: datetime


class DecisionResponse(APIModel):
    decision_id: str
    deal_id: str
    decision_code: str
    decided_by_type: DecisionByType
    decided_by_ref: str | None
    rationale: str | None
    payload_json: dict | None
    created_at: datetime

