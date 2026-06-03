from datetime import datetime

from src.shared.enums import ApprovalDecision, ApprovalStatus
from src.shared.types.common import APIModel


class BuildCEOApprovalRequest(APIModel):
    deal_id: str
    finance_memo_set_id: str
    integrated_risk_memo_set_id: str


class CEOApprovalConditionInput(APIModel):
    condition_code: str
    condition_text: str


class RecordCEODecisionRequest(APIModel):
    ceo_approval_set_id: str
    decision: ApprovalDecision
    decided_by_ref: str | None = None
    rationale: str
    conditions: list[CEOApprovalConditionInput] = []


class CEOApprovalConditionResponse(APIModel):
    condition_code: str
    condition_text: str
    created_at: datetime


class CEOApprovalRecordResponse(APIModel):
    ceo_approval_id: str
    ceo_approval_set_id: str
    decision: ApprovalDecision
    decided_by_ref: str | None
    rationale: str
    decided_at: datetime
    created_at: datetime
    updated_at: datetime
    conditions: list[CEOApprovalConditionResponse]


class CEOApprovalSetResponse(APIModel):
    ceo_approval_set_id: str
    deal_id: str
    finance_memo_set_id: str
    integrated_risk_memo_set_id: str
    approval_status: ApprovalStatus
    created_at: datetime
    updated_at: datetime
    records: list[CEOApprovalRecordResponse]
