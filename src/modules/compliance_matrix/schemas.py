from datetime import datetime

from src.shared.enums import ComplianceStatus
from src.shared.types.common import APIModel


class BuildComplianceMatrixRequest(APIModel):
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str


class ComplianceMatrixRowResponse(APIModel):
    row_code: str
    sequence_no: int
    requirement_text: str
    requirement_category: str
    compliance_status: ComplianceStatus
    source_artifact_ref: str | None
    source_pointer: str | None
    notes: str | None
    is_mandatory: bool
    requires_manual_review: bool
    created_at: datetime


class ComplianceMatrixResponse(APIModel):
    compliance_matrix_id: str
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    matrix_row_count: int
    ambiguous_row_count: int
    high_risk_row_count: int
    requires_manual_review: bool
    created_at: datetime
    updated_at: datetime
    rows: list[ComplianceMatrixRowResponse]

