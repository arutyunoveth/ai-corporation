from datetime import datetime

from src.shared.enums import BidCompletenessStatus, RiskSeverity
from src.shared.types.common import APIModel


class CheckBidCompletenessRequest(APIModel):
    deal_id: str
    bid_package_set_id: str
    document_requirement_set_id: str


class BidCompletenessFlagResponse(APIModel):
    flag_code: str
    severity: RiskSeverity
    summary: str
    source_ref: str | None
    created_at: datetime


class BidCompletenessRecordResponse(APIModel):
    bid_completeness_id: str
    bid_completeness_set_id: str
    mandatory_total: int
    mandatory_present: int
    optional_present: int
    summary_text: str
    created_at: datetime
    updated_at: datetime
    flags: list[BidCompletenessFlagResponse]


class BidCompletenessSetResponse(APIModel):
    bid_completeness_set_id: str
    deal_id: str
    bid_package_set_id: str
    completeness_status: BidCompletenessStatus
    created_at: datetime
    updated_at: datetime
    records: list[BidCompletenessRecordResponse]
