from datetime import datetime

from pydantic import Field

from src.shared.enums import PrioritizationStatus
from src.shared.types.common import APIModel


class BuildIntakePriorityRequest(APIModel):
    deal_id: str


class IntakePriorityFactorResponse(APIModel):
    factor_code: str
    factor_value: float
    rationale: str
    created_at: datetime


class IntakePriorityRecordResponse(APIModel):
    intake_priority_id: str
    intake_priority_set_id: str
    priority_score: float
    summary_text: str
    recommended_queue_position: int
    created_at: datetime
    updated_at: datetime
    factors: list[IntakePriorityFactorResponse] = Field(default_factory=list)


class IntakePrioritySetResponse(APIModel):
    intake_priority_set_id: str
    deal_id: str
    prioritization_status: PrioritizationStatus
    created_at: datetime
    updated_at: datetime
    records: list[IntakePriorityRecordResponse] = Field(default_factory=list)
