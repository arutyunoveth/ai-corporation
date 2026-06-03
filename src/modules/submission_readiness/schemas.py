from datetime import datetime

from src.shared.enums import ReadinessRecommendation, RiskSeverity, SubmissionReadinessStatus
from src.shared.types.common import APIModel


class BuildSubmissionReadinessRequest(APIModel):
    deal_id: str
    bid_completeness_set_id: str
    ceo_approval_set_id: str
    finance_memo_set_id: str
    integrated_risk_memo_set_id: str


class SubmissionReadinessFlagResponse(APIModel):
    flag_code: str
    severity: RiskSeverity
    summary: str
    source_ref: str | None
    created_at: datetime


class SubmissionReadinessRecordResponse(APIModel):
    submission_readiness_id: str
    submission_readiness_set_id: str
    recommendation: ReadinessRecommendation
    summary_text: str
    created_at: datetime
    updated_at: datetime
    flags: list[SubmissionReadinessFlagResponse]


class SubmissionReadinessSetResponse(APIModel):
    submission_readiness_set_id: str
    deal_id: str
    bid_completeness_set_id: str
    ceo_approval_set_id: str
    finance_memo_set_id: str
    integrated_risk_memo_set_id: str
    readiness_status: SubmissionReadinessStatus
    created_at: datetime
    updated_at: datetime
    records: list[SubmissionReadinessRecordResponse]
