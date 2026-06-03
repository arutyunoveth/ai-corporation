from datetime import datetime

from src.shared.enums import ScreeningResultStatus
from src.shared.types.common import APIModel


class RunScreeningRequest(APIModel):
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str


class TenderScreeningResponse(APIModel):
    screening_id: str
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    result_status: ScreeningResultStatus
    screening_score: float
    rationale_text: str
    factor_breakdown_json: dict
    reason_codes_json: list
    recommended_next_status: str | None
    created_at: datetime
    updated_at: datetime

