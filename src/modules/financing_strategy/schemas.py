from datetime import datetime

from src.shared.enums import FinancingFeasibilityStatus, FinancingStrategyStatus
from src.shared.types.common import APIModel


class BuildFinancingStrategyRequest(APIModel):
    deal_id: str
    cash_gap_set_id: str


class FinancingStrategyOptionResponse(APIModel):
    option_code: str
    option_name: str
    funding_amount: float
    funding_cost: float
    currency_code: str
    feasibility_status: FinancingFeasibilityStatus
    created_at: datetime


class FinancingStrategyRecordResponse(APIModel):
    financing_strategy_id: str
    financing_strategy_set_id: str
    recommended_option_code: str
    feasible: bool
    notes: str | None
    created_at: datetime
    updated_at: datetime
    options: list[FinancingStrategyOptionResponse]


class FinancingStrategySetResponse(APIModel):
    financing_strategy_set_id: str
    deal_id: str
    cash_gap_set_id: str
    strategy_status: FinancingStrategyStatus
    created_at: datetime
    updated_at: datetime
    records: list[FinancingStrategyRecordResponse]
