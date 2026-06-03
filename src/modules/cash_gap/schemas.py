from datetime import datetime

from src.shared.enums import CashGapStatus
from src.shared.types.common import APIModel


class BuildCashGapRequest(APIModel):
    deal_id: str
    cost_model_set_id: str


class CashGapScenarioResponse(APIModel):
    scenario_code: str
    scenario_name: str
    peak_gap_amount: float
    gap_duration_days: int
    created_at: datetime


class CashGapRecordResponse(APIModel):
    cash_gap_id: str
    cash_gap_set_id: str
    peak_gap_amount: float
    gap_duration_days: int
    currency_code: str
    notes: str | None
    created_at: datetime
    updated_at: datetime
    scenarios: list[CashGapScenarioResponse]


class CashGapSetResponse(APIModel):
    cash_gap_set_id: str
    deal_id: str
    cost_model_set_id: str
    cash_gap_status: CashGapStatus
    created_at: datetime
    updated_at: datetime
    records: list[CashGapRecordResponse]
