from datetime import datetime

from src.shared.enums import PostmortemActionStatus, PostmortemStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildPostmortemRequest(APIModel):
    deal_id: str


class PostmortemFindingResponse(APIModel):
    finding_code: str
    severity: RiskSeverity
    summary: str
    created_at: datetime


class PostmortemActionItemResponse(APIModel):
    action_code: str
    owner_hint: str | None
    summary: str
    action_status: PostmortemActionStatus
    created_at: datetime


class PostmortemRecordResponse(APIModel):
    postmortem_id: str
    summary_text: str
    root_cause_summary: str
    recommendation_summary: str
    created_at: datetime
    updated_at: datetime
    findings: list[PostmortemFindingResponse]
    action_items: list[PostmortemActionItemResponse]


class PostmortemSetResponse(APIModel):
    postmortem_set_id: str
    deal_id: str
    deal_closure_report_set_id: str
    incident_register_set_id: str | None
    claim_trigger_set_id: str | None
    kpi_learning_set_id: str | None
    postmortem_status: PostmortemStatus
    created_at: datetime
    updated_at: datetime
    records: list[PostmortemRecordResponse]
