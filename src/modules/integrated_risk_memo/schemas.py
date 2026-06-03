from datetime import datetime

from src.shared.enums import ApprovalDecision, IntegratedRiskMemoStatus, RiskSeverity, RiskSourceType
from src.shared.types.common import APIModel


class BuildIntegratedRiskMemoRequest(APIModel):
    deal_id: str
    initial_tech_risk_flag_set_id: str
    supplier_verification_set_id: str
    quote_comparison_set_id: str
    finance_memo_set_id: str
    contract_risk_set_id: str


class IntegratedRiskItemResponse(APIModel):
    risk_source_type: RiskSourceType
    source_object_ref: str
    severity: RiskSeverity
    summary: str
    mitigation_hint: str | None
    created_at: datetime


class IntegratedRiskMemoRecordResponse(APIModel):
    integrated_risk_memo_id: str
    integrated_risk_memo_set_id: str
    summary_text: str
    structured_summary_json: dict
    recommendation: ApprovalDecision
    created_at: datetime
    updated_at: datetime
    items: list[IntegratedRiskItemResponse]


class IntegratedRiskMemoSetResponse(APIModel):
    integrated_risk_memo_set_id: str
    deal_id: str
    initial_tech_risk_flag_set_id: str
    supplier_verification_set_id: str
    quote_comparison_set_id: str
    finance_memo_set_id: str
    contract_risk_set_id: str
    memo_status: IntegratedRiskMemoStatus
    created_at: datetime
    updated_at: datetime
    records: list[IntegratedRiskMemoRecordResponse]
