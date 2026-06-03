from src.modules.cash_gap.models import CashGapRecord, CashGapScenario, CashGapSet
from src.modules.cost_model.models import CostModelLine, CostModelRecord, CostModelSet
from src.modules.event_log.models import EventRecord
from src.modules.finance_memo.models import FinanceMemoFlag, FinanceMemoRecord, FinanceMemoSet
from src.modules.financing_strategy.models import (
    FinancingStrategyOption,
    FinancingStrategyRecord,
    FinancingStrategySet,
)
from tests.test_sprint3b_integration import _prepare_supplier_package


def _prepare_economics_prerequisites(client):
    intake, shortlist, _rfq_batch, _communication_set, quote_set_id = _prepare_supplier_package(client)
    verification = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()
    comparison = client.post(
        "/quote-comparison/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_set_id": quote_set_id,
            "supplier_verification_set_id": verification["supplier_verification_set_id"],
        },
    ).json()
    return intake, comparison


def test_build_cost_model_and_persist_lines(client, session):
    intake, comparison = _prepare_economics_prerequisites(client)

    response = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    cost_model_set = session.query(CostModelSet).filter_by(
        cost_model_set_id=payload["cost_model_set_id"]
    ).one()
    record = session.query(CostModelRecord).filter_by(
        cost_model_set_id=payload["cost_model_set_id"]
    ).one()
    lines = session.query(CostModelLine).filter_by(cost_model_id=record.cost_model_id).all()

    assert cost_model_set.deal_id == intake["deal_id"]
    assert record.min_viable_bid > record.total_cost > 0
    assert len(lines) == 4


def test_build_cash_gap_and_persist_scenarios(client, session):
    intake, comparison = _prepare_economics_prerequisites(client)
    cost_model = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    ).json()

    response = client.post(
        "/cash-gap/build",
        json={"deal_id": intake["deal_id"], "cost_model_set_id": cost_model["cost_model_set_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    cash_gap_set = session.query(CashGapSet).filter_by(cash_gap_set_id=payload["cash_gap_set_id"]).one()
    record = session.query(CashGapRecord).filter_by(cash_gap_set_id=payload["cash_gap_set_id"]).one()
    scenarios = session.query(CashGapScenario).filter_by(cash_gap_id=record.cash_gap_id).all()

    assert cash_gap_set.deal_id == intake["deal_id"]
    assert record.peak_gap_amount > 0
    assert record.gap_duration_days > 0
    assert len(scenarios) == 3


def test_build_financing_strategy_and_persist_options(client, session):
    intake, comparison = _prepare_economics_prerequisites(client)
    cost_model = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    ).json()
    cash_gap = client.post(
        "/cash-gap/build",
        json={"deal_id": intake["deal_id"], "cost_model_set_id": cost_model["cost_model_set_id"]},
    ).json()

    response = client.post(
        "/financing-strategy/build",
        json={"deal_id": intake["deal_id"], "cash_gap_set_id": cash_gap["cash_gap_set_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    strategy_set = session.query(FinancingStrategySet).filter_by(
        financing_strategy_set_id=payload["financing_strategy_set_id"]
    ).one()
    record = session.query(FinancingStrategyRecord).filter_by(
        financing_strategy_set_id=payload["financing_strategy_set_id"]
    ).one()
    options = session.query(FinancingStrategyOption).filter_by(
        financing_strategy_id=record.financing_strategy_id
    ).all()

    assert strategy_set.deal_id == intake["deal_id"]
    assert record.recommended_option_code
    assert len(options) == 3


def test_build_finance_memo_and_persist_flags_recommendation(client, session):
    intake, comparison = _prepare_economics_prerequisites(client)
    cost_model = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    ).json()
    cash_gap = client.post(
        "/cash-gap/build",
        json={"deal_id": intake["deal_id"], "cost_model_set_id": cost_model["cost_model_set_id"]},
    ).json()
    financing = client.post(
        "/financing-strategy/build",
        json={"deal_id": intake["deal_id"], "cash_gap_set_id": cash_gap["cash_gap_set_id"]},
    ).json()

    response = client.post(
        "/finance-memo/build",
        json={
            "deal_id": intake["deal_id"],
            "cost_model_set_id": cost_model["cost_model_set_id"],
            "cash_gap_set_id": cash_gap["cash_gap_set_id"],
            "financing_strategy_set_id": financing["financing_strategy_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    memo_set = session.query(FinanceMemoSet).filter_by(
        finance_memo_set_id=payload["finance_memo_set_id"]
    ).one()
    record = session.query(FinanceMemoRecord).filter_by(
        finance_memo_set_id=payload["finance_memo_set_id"]
    ).one()
    flags = session.query(FinanceMemoFlag).filter_by(finance_memo_id=record.finance_memo_id).all()

    assert memo_set.deal_id == intake["deal_id"]
    assert record.recommendation in {"GO", "GO_WITH_CONDITIONS", "NO_GO", "NEEDS_REVIEW"}
    assert isinstance(record.structured_summary_json, dict)
    assert len(flags) >= 0


def test_sprint4a_outputs_linked_to_deal_and_events_written(client, session):
    intake, comparison = _prepare_economics_prerequisites(client)
    cost_model = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    ).json()
    cash_gap = client.post(
        "/cash-gap/build",
        json={"deal_id": intake["deal_id"], "cost_model_set_id": cost_model["cost_model_set_id"]},
    ).json()
    financing = client.post(
        "/financing-strategy/build",
        json={"deal_id": intake["deal_id"], "cash_gap_set_id": cash_gap["cash_gap_set_id"]},
    ).json()
    finance_memo = client.post(
        "/finance-memo/build",
        json={
            "deal_id": intake["deal_id"],
            "cost_model_set_id": cost_model["cost_model_set_id"],
            "cash_gap_set_id": cash_gap["cash_gap_set_id"],
            "financing_strategy_set_id": financing["financing_strategy_set_id"],
        },
    ).json()

    assert session.query(CostModelSet).filter_by(
        cost_model_set_id=cost_model["cost_model_set_id"], deal_id=intake["deal_id"]
    ).count() == 1
    assert session.query(CashGapSet).filter_by(
        cash_gap_set_id=cash_gap["cash_gap_set_id"], deal_id=intake["deal_id"]
    ).count() == 1
    assert session.query(FinancingStrategySet).filter_by(
        financing_strategy_set_id=financing["financing_strategy_set_id"], deal_id=intake["deal_id"]
    ).count() == 1
    assert session.query(FinanceMemoSet).filter_by(
        finance_memo_set_id=finance_memo["finance_memo_set_id"], deal_id=intake["deal_id"]
    ).count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=intake["deal_id"]).all()}
    assert "cost_model_build_started" in event_codes
    assert "cost_model_built" in event_codes
    assert "cash_gap_build_started" in event_codes
    assert "cash_gap_built" in event_codes
    assert "financing_strategy_build_started" in event_codes
    assert "financing_strategy_built" in event_codes
    assert "finance_memo_build_started" in event_codes
    assert "finance_memo_built" in event_codes


def test_finance_memo_requires_upstream_economics_objects(client):
    intake, _comparison = _prepare_economics_prerequisites(client)
    response = client.post(
        "/finance-memo/build",
        json={
            "deal_id": intake["deal_id"],
            "cost_model_set_id": "CMS-2026-999999",
            "cash_gap_set_id": "CGS-2026-999999",
            "financing_strategy_set_id": "FSS-2026-999999",
        },
    )
    assert response.status_code == 404


def test_sprint4a_reruns_are_append_only(client, session):
    intake, comparison = _prepare_economics_prerequisites(client)

    first_cost_model = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    ).json()
    second_cost_model = client.post(
        "/cost-model/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_comparison_set_id": comparison["quote_comparison_set_id"],
        },
    ).json()

    assert first_cost_model["cost_model_set_id"] != second_cost_model["cost_model_set_id"]

    first_cash_gap = client.post(
        "/cash-gap/build",
        json={"deal_id": intake["deal_id"], "cost_model_set_id": first_cost_model["cost_model_set_id"]},
    ).json()
    second_cash_gap = client.post(
        "/cash-gap/build",
        json={"deal_id": intake["deal_id"], "cost_model_set_id": second_cost_model["cost_model_set_id"]},
    ).json()

    assert first_cash_gap["cash_gap_set_id"] != second_cash_gap["cash_gap_set_id"]
    assert session.query(CostModelSet).filter_by(deal_id=intake["deal_id"]).count() == 2
    assert session.query(CashGapSet).filter_by(deal_id=intake["deal_id"]).count() == 2
