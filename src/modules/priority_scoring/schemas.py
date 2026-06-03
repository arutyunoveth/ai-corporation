from datetime import datetime

from src.shared.enums import PriorityBucket
from src.shared.types.common import APIModel


class RunPriorityScoringRequest(APIModel):
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    screening_id: str


class PriorityScoreResponse(APIModel):
    priority_score_id: str
    deal_id: str
    intake_id: str
    document_set_id: str
    tender_summary_id: str
    screening_id: str
    priority_score: float
    priority_bucket: PriorityBucket
    rationale_text: str
    factor_breakdown_json: dict
    created_at: datetime
    updated_at: datetime

