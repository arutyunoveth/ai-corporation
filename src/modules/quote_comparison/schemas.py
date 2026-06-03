from datetime import datetime

from src.shared.enums import QuoteComparisonStatus
from src.shared.types.common import APIModel


class BuildQuoteComparisonRequest(APIModel):
    deal_id: str
    quote_set_id: str
    supplier_verification_set_id: str


class QuoteComparisonRowResponse(APIModel):
    quote_id: str
    supplier_id: str
    price_score: float
    delivery_score: float
    quality_score: float
    total_score: float
    rank_order: int
    comparison_notes: str | None
    created_at: datetime


class QuoteComparisonRecommendationResponse(APIModel):
    quote_comparison_set_id: str
    recommended_quote_id: str
    recommended_supplier_id: str
    rationale: str
    created_at: datetime


class QuoteComparisonSetResponse(APIModel):
    quote_comparison_set_id: str
    deal_id: str
    quote_set_id: str
    supplier_verification_set_id: str
    comparison_status: QuoteComparisonStatus
    created_at: datetime
    updated_at: datetime
    rows: list[QuoteComparisonRowResponse]
    recommendation: QuoteComparisonRecommendationResponse | None = None
