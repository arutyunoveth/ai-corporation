from datetime import datetime

from src.shared.enums import ClosingDocItemStatus, ClosingDocsStatus, RiskSeverity
from src.shared.types.common import APIModel


class BuildClosingDocsRequest(APIModel):
    deal_id: str


class ClosingDocsItemResponse(APIModel):
    item_code: str
    artifact_ref: str | None
    item_status: ClosingDocItemStatus
    created_at: datetime


class ClosingDocsFlagResponse(APIModel):
    flag_code: str
    severity: RiskSeverity
    summary: str
    created_at: datetime


class ClosingDocsRecordResponse(APIModel):
    closing_docs_id: str
    docs_manifest_json: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    items: list[ClosingDocsItemResponse]
    flags: list[ClosingDocsFlagResponse]


class ClosingDocsSetResponse(APIModel):
    closing_docs_set_id: str
    deal_id: str
    docs_status: ClosingDocsStatus
    created_at: datetime
    updated_at: datetime
    records: list[ClosingDocsRecordResponse]
