from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.modules.cash_gap.service import get_cash_gap_set
from src.modules.cost_model.service import get_cost_model_set
from src.modules.financing_strategy.service import get_financing_strategy_set
from src.modules.quote_comparison.service import get_quote_comparison_set
from src.shared.validation import require_same_reference


@dataclass(slots=True)
class EconomicsPackage:
    deal_id: str
    quote_comparison_set: object | None = None
    quote_comparison_rows: list | None = None
    quote_comparison_recommendation: object | None = None
    cost_model_set: object | None = None
    cost_model_records: list | None = None
    cash_gap_set: object | None = None
    cash_gap_records: list | None = None
    financing_strategy_set: object | None = None
    financing_strategy_records: list | None = None


def load_economics_package(
    session: Session,
    *,
    deal_id: str,
    quote_comparison_set_id: str | None = None,
    cost_model_set_id: str | None = None,
    cash_gap_set_id: str | None = None,
    financing_strategy_set_id: str | None = None,
) -> EconomicsPackage:
    package = EconomicsPackage(deal_id=deal_id)

    if quote_comparison_set_id:
        comparison_set, rows, recommendation = get_quote_comparison_set(session, quote_comparison_set_id)
        require_same_reference(deal_id, comparison_set.deal_id, "deal_id")
        package.quote_comparison_set = comparison_set
        package.quote_comparison_rows = rows
        package.quote_comparison_recommendation = recommendation

    if cost_model_set_id:
        cost_model_set, records = get_cost_model_set(session, cost_model_set_id)
        require_same_reference(deal_id, cost_model_set.deal_id, "deal_id")
        package.cost_model_set = cost_model_set
        package.cost_model_records = records

    if cash_gap_set_id:
        cash_gap_set, records = get_cash_gap_set(session, cash_gap_set_id)
        require_same_reference(deal_id, cash_gap_set.deal_id, "deal_id")
        package.cash_gap_set = cash_gap_set
        package.cash_gap_records = records

    if financing_strategy_set_id:
        strategy_set, records = get_financing_strategy_set(session, financing_strategy_set_id)
        require_same_reference(deal_id, strategy_set.deal_id, "deal_id")
        package.financing_strategy_set = strategy_set
        package.financing_strategy_records = records

    return package
