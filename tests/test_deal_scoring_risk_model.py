from __future__ import annotations

from src.modules.deal_scoring.risk_model import assess_risk


class TestRiskModel:
    def test_low_risk(self):
        result = assess_risk(
            unknown_delivery_count=0,
            manual_force_include_count=0,
            low_relevance_used_count=0,
            overbuy_required_count=0,
            captcha_blocked_count=0,
            needs_manual_tax_review=False,
            risky_supplier_count=0,
            insufficient_quantity_count=0,
            blocked_supplier_used=False,
        )
        assert result.risk_level == "low"
        assert result.risk_penalty == 0.0

    def test_medium_risk(self):
        result = assess_risk(
            unknown_delivery_count=3,
            manual_force_include_count=1,
            low_relevance_used_count=0,
            overbuy_required_count=0,
            captcha_blocked_count=0,
            needs_manual_tax_review=False,
            risky_supplier_count=0,
            insufficient_quantity_count=0,
            blocked_supplier_used=False,
        )
        assert result.risk_level == "medium"
        assert result.risk_penalty == 25.0

    def test_high_risk(self):
        result = assess_risk(
            unknown_delivery_count=0,
            manual_force_include_count=0,
            low_relevance_used_count=2,
            overbuy_required_count=2,
            captcha_blocked_count=0,
            needs_manual_tax_review=False,
            risky_supplier_count=1,
            insufficient_quantity_count=0,
            blocked_supplier_used=False,
        )
        assert result.risk_level == "high"
        assert result.risk_penalty == 60.0

    def test_critical_risk_blocked_supplier(self):
        result = assess_risk(
            unknown_delivery_count=0,
            manual_force_include_count=0,
            low_relevance_used_count=0,
            overbuy_required_count=0,
            captcha_blocked_count=0,
            needs_manual_tax_review=False,
            risky_supplier_count=0,
            insufficient_quantity_count=0,
            blocked_supplier_used=True,
        )
        assert result.risk_level == "critical"
        assert result.risk_penalty == 100.0
        assert "blocked_supplier_used" in result.reasons

    def test_critical_risk_insufficient_quantity(self):
        result = assess_risk(
            unknown_delivery_count=0,
            manual_force_include_count=0,
            low_relevance_used_count=0,
            overbuy_required_count=0,
            captcha_blocked_count=0,
            needs_manual_tax_review=False,
            risky_supplier_count=0,
            insufficient_quantity_count=3,
            blocked_supplier_used=False,
        )
        assert result.risk_level == "critical"
        assert result.risk_penalty == 150.0

    def test_tax_review_adds_penalty(self):
        result = assess_risk(
            unknown_delivery_count=0,
            manual_force_include_count=0,
            low_relevance_used_count=0,
            overbuy_required_count=0,
            captcha_blocked_count=0,
            needs_manual_tax_review=True,
            risky_supplier_count=0,
            insufficient_quantity_count=0,
            blocked_supplier_used=False,
        )
        assert result.risk_penalty == 15.0
        assert "needs_manual_tax_review" in result.reasons
