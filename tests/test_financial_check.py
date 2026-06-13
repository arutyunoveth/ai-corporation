from __future__ import annotations

from decimal import Decimal

from src.modules.financial_check.check import (
    check_purchase_financials,
    escalate_risk_level,
    FinancialCheckResult,
)


class TestEscalateRiskLevel:
    def test_warning_bumps_once(self):
        assert escalate_risk_level("low", "warning") == "medium"

    def test_error_bumps_twice(self):
        assert escalate_risk_level("low", "error") == "high"

    def test_stays_at_max(self):
        assert escalate_risk_level("critical", "error") == "critical"

    def test_default_base(self):
        assert escalate_risk_level(None, "warning") == "high"


class TestFinancialCheck:
    def test_ok(self):
        result = check_purchase_financials(
            max_total_price=Decimal("100000"),
            margin_after_tax_percent=25.0,
            profit_after_tax=25000.0,
            cash_required=50000.0,
            offers=[{"price": 100}],
        )
        assert result.status == "ok"

    def test_warning_unknown_max_price(self):
        result = check_purchase_financials(
            max_total_price=None,
            margin_after_tax_percent=25.0,
            profit_after_tax=25000.0,
            cash_required=50000.0,
            offers=[{"price": 100}],
        )
        assert result.status == "warning"

    def test_warning_negative_margin(self):
        result = check_purchase_financials(
            max_total_price=Decimal("100000"),
            margin_after_tax_percent=-5.0,
            profit_after_tax=25000.0,
            cash_required=50000.0,
            offers=[{"price": 100}],
        )
        assert result.status == "warning"

    def test_error_negative_profit(self):
        result = check_purchase_financials(
            max_total_price=Decimal("100000"),
            margin_after_tax_percent=25.0,
            profit_after_tax=-5000.0,
            cash_required=50000.0,
            offers=[{"price": 100}],
        )
        assert result.status == "error"

    def test_error_negative_cash(self):
        result = check_purchase_financials(
            max_total_price=Decimal("100000"),
            margin_after_tax_percent=25.0,
            profit_after_tax=25000.0,
            cash_required=-1000.0,
            offers=[{"price": 100}],
        )
        assert result.status == "error"

    def test_warning_cash_exceeds_price(self):
        result = check_purchase_financials(
            max_total_price=Decimal("50000"),
            margin_after_tax_percent=25.0,
            profit_after_tax=25000.0,
            cash_required=60000.0,
            offers=[{"price": 100}],
        )
        assert result.status == "warning"

    def test_warning_no_offers(self):
        result = check_purchase_financials(
            max_total_price=Decimal("100000"),
            margin_after_tax_percent=25.0,
            profit_after_tax=25000.0,
            cash_required=50000.0,
            offers=[],
        )
        assert result.status == "warning"

    def test_warning_max_price_zero(self):
        result = check_purchase_financials(
            max_total_price=Decimal("0"),
            margin_after_tax_percent=25.0,
            profit_after_tax=25000.0,
            cash_required=50000.0,
            offers=[{"price": 100}],
        )
        assert result.status == "error"

    def test_all_warnings(self):
        result = check_purchase_financials(
            max_total_price=None,
            margin_after_tax_percent=None,
            profit_after_tax=25000.0,
            cash_required=None,
            offers=[{"price": 100}],
        )
        assert result.status == "warning"
        assert len(result.warnings) >= 3
