from datetime import datetime

from src.shared.enums import ClaimTriggerStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildClaimTriggerRequest(APIModel):
    deal_id: str


class ClaimTriggerFlagResponse(APIModel):
    flag_code: str
    severity: RiskSeverity
    summary: str
    created_at: datetime


class ClaimTriggerLinkResponse(APIModel):
    source_ref: str
    created_at: datetime


class ClaimTriggerRecordResponse(APIModel):
    claim_trigger_id: str
    summary_text: str
    trigger_reason: str
    created_at: datetime
    updated_at: datetime
    flags: list[ClaimTriggerFlagResponse]
    links: list[ClaimTriggerLinkResponse]


class ClaimTriggerSetResponse(APIModel):
    claim_trigger_set_id: str
    deal_id: str
    trigger_status: ClaimTriggerStatus
    created_at: datetime
    updated_at: datetime
    records: list[ClaimTriggerRecordResponse]
