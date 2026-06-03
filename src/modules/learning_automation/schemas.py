from datetime import datetime

from src.shared.enums import (
    LearningAutomationScopeType,
    LearningAutomationStatus,
    LearningRecommendationType,
)
from src.shared.types.common import APIModel


class BuildLearningAutomationRequest(APIModel):
    scope_type: LearningAutomationScopeType
    scope_ref: str
    deal_closure_set_id: str | None = None
    kpi_learning_set_id: str | None = None


class LearningRecommendationRecordResponse(APIModel):
    recommendation_code: str
    recommendation_type: LearningRecommendationType
    recommendation_text: str
    source_ref: str | None
    created_at: datetime


class LearningAutomationRecordResponse(APIModel):
    learning_automation_id: str
    learning_automation_set_id: str
    summary_text: str
    created_at: datetime
    updated_at: datetime
    recommendations: list[LearningRecommendationRecordResponse]


class LearningAutomationSetResponse(APIModel):
    learning_automation_set_id: str
    scope_type: LearningAutomationScopeType
    scope_ref: str
    automation_status: LearningAutomationStatus
    created_at: datetime
    updated_at: datetime
    records: list[LearningAutomationRecordResponse]
