from datetime import datetime

from src.shared.enums import TechRiskCategory, TechRiskSeverity
from src.shared.types.common import APIModel


class BuildInitialTechRisksRequest(APIModel):
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    compliance_matrix_id: str
    document_requirement_set_id: str


class InitialTechRiskFlagResponse(APIModel):
    row_code: str
    risk_code: str
    risk_category: TechRiskCategory
    severity: TechRiskSeverity
    summary: str
    source_ref: str | None
    mitigation_hint: str | None
    created_at: datetime
    requires_manual_review: bool


class InitialTechRiskFlagSetResponse(APIModel):
    risk_flag_set_id: str
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    compliance_matrix_id: str
    document_requirement_set_id: str
    risk_flag_count: int
    overall_risk_severity: TechRiskSeverity
    summary_text: str
    created_at: datetime
    updated_at: datetime
    flags: list[InitialTechRiskFlagResponse]

