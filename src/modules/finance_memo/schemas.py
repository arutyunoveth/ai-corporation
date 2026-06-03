from datetime import datetime

from src.shared.enums import FinanceMemoStatus, FinanceRecommendation
from src.shared.types.common import APIModel


class BuildFinanceMemoRequest(APIModel):
    deal_id: str
    cost_model_set_id: str
    cash_gap_set_id: str
    financing_strategy_set_id: str


class FinanceMemoFlagResponse(APIModel):
    flag_code: str
    severity: str
    summary: str
    created_at: datetime


class FinanceMemoRecordResponse(APIModel):
    finance_memo_id: str
    finance_memo_set_id: str
    summary_text: str
    structured_summary_json: dict
    recommendation: FinanceRecommendation
    created_at: datetime
    updated_at: datetime
    flags: list[FinanceMemoFlagResponse]


class FinanceMemoSetResponse(APIModel):
    finance_memo_set_id: str
    deal_id: str
    cost_model_set_id: str
    cash_gap_set_id: str
    financing_strategy_set_id: str
    memo_status: FinanceMemoStatus
    created_at: datetime
    updated_at: datetime
    records: list[FinanceMemoRecordResponse]
