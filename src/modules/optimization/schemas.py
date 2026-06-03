from datetime import datetime

from src.shared.enums import OptimizationRecommendationType, OptimizationScopeType, OptimizationStatus
from src.shared.types.common import APIModel


class BuildOptimizationRequest(APIModel):
    scope_type: OptimizationScopeType
    scope_ref: str


class OptimizationSignalRecordResponse(APIModel):
    signal_code: str
    signal_value_text: str
    source_ref: str | None
    created_at: datetime


class OptimizationRecommendationRecordResponse(APIModel):
    optimization_recommendation_id: str
    optimization_recommendation_set_id: str
    recommendation_code: str
    recommendation_type: OptimizationRecommendationType
    recommendation_text: str
    confidence_score: float | None
    created_at: datetime
    updated_at: datetime
    signals: list[OptimizationSignalRecordResponse]


class OptimizationRecommendationSetResponse(APIModel):
    optimization_recommendation_set_id: str
    scope_type: OptimizationScopeType
    scope_ref: str
    optimization_status: OptimizationStatus
    created_at: datetime
    updated_at: datetime
    records: list[OptimizationRecommendationRecordResponse]
