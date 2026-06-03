from datetime import datetime

from src.shared.enums import DocumentRequirementStatus
from src.shared.types.common import APIModel


class ExtractDocumentRequirementsRequest(APIModel):
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str


class DocumentRequirementRowResponse(APIModel):
    row_code: str
    sequence_no: int
    requirement_title: str
    requirement_description: str
    requirement_category: str
    requirement_status: DocumentRequirementStatus
    source_artifact_ref: str | None
    source_pointer: str | None
    notes: str | None
    requires_manual_review: bool
    created_at: datetime


class DocumentRequirementSetResponse(APIModel):
    document_requirement_set_id: str
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    requirement_count: int
    requires_manual_review: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    rows: list[DocumentRequirementRowResponse]

