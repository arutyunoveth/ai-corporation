from datetime import datetime

from src.shared.enums import CostLineType, CostModelStatus
from src.shared.types.common import APIModel


class BuildCostModelRequest(APIModel):
    deal_id: str
    quote_comparison_set_id: str


class CostModelLineResponse(APIModel):
    line_code: str
    line_type: CostLineType
    amount: float
    currency_code: str
    notes: str | None
    created_at: datetime


class CostModelRecordResponse(APIModel):
    cost_model_id: str
    cost_model_set_id: str
    base_quote_total: float
    logistics_cost: float
    buffer_cost: float
    overhead_cost: float
    total_cost: float
    min_viable_bid: float
    currency_code: str
    created_at: datetime
    updated_at: datetime
    lines: list[CostModelLineResponse]


class CostModelSetResponse(APIModel):
    cost_model_set_id: str
    deal_id: str
    quote_comparison_set_id: str
    cost_model_status: CostModelStatus
    created_at: datetime
    updated_at: datetime
    records: list[CostModelRecordResponse]
