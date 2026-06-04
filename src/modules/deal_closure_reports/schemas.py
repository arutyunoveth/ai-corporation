from datetime import datetime

from src.shared.enums import DealClosureReportStatus
from src.shared.types.common import APIModel


class BuildDealClosureReportRequest(APIModel):
    deal_id: str


class DealClosureReportLinkResponse(APIModel):
    source_ref: str
    created_at: datetime


class DealClosureReportRecordResponse(APIModel):
    deal_closure_report_id: str
    report_code: str
    summary_text: str
    closure_health: str
    created_at: datetime
    updated_at: datetime
    links: list[DealClosureReportLinkResponse]


class DealClosureReportSetResponse(APIModel):
    deal_closure_report_set_id: str
    deal_id: str
    deal_closure_set_id: str
    acceptance_control_set_id: str | None
    closing_docs_set_id: str | None
    payment_tracking_set_id: str | None
    claim_trigger_set_id: str | None
    report_status: DealClosureReportStatus
    created_at: datetime
    updated_at: datetime
    records: list[DealClosureReportRecordResponse]
