from datetime import datetime

from src.shared.enums import TenderSummaryStatus
from src.shared.types.common import APIModel


class BuildTenderSummaryRequest(APIModel):
    deal_id: str
    intake_id: str
    document_set_id: str


class BuildTenderSummaryResponse(APIModel):
    tender_summary_id: str
    summary_status: TenderSummaryStatus


class TenderSummarySourceLinkResponse(APIModel):
    source_object_type: str
    source_object_ref: str
    created_at: datetime


class TenderSummaryResponse(APIModel):
    tender_summary_id: str
    deal_id: str
    intake_id: str
    document_set_id: str
    summary_status: TenderSummaryStatus
    summary_text: str
    structured_summary_json: dict
    created_at: datetime
    updated_at: datetime
    source_links: list[TenderSummarySourceLinkResponse]
