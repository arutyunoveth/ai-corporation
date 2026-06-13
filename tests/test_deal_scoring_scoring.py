from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.modules.deal_scoring.scoring import (
    _margin_score,
    _profit_score,
    _deadline_score,
    _data_quality_score,
    _supplier_quality_score,
    _cash_efficiency_score,
    _competition_score,
    calculate_purchase_score,
)


class TestMarginScore:
    def test_very_high(self):
        assert _margin_score(40) == 30

    def test_high(self):
        assert _margin_score(30) == 20

    def test_moderate(self):
        assert _margin_score(22) == 10

    def test_low(self):
        assert _margin_score(15) == 0

    def test_negative(self):
        assert _margin_score(5) == -30


class TestProfitScore:
    def test_very_high(self):
        assert _profit_score(150000) == 30

    def test_high(self):
        assert _profit_score(60000) == 20

    def test_moderate(self):
        assert _profit_score(25000) == 10

    def test_low(self):
        assert _profit_score(10000) == 5

    def test_minimal(self):
        assert _profit_score(1000) == 0


class TestDeadlineScore:
    def test_future(self):
        future = datetime.now() + timedelta(days=2)
        score, status = _deadline_score(future)
        assert score == 10
        assert status == "active"

    def test_near_deadline(self):
        future = datetime.now() + timedelta(hours=6)
        score, status = _deadline_score(future)
        assert score == -10
        assert status == "deadline_soon"

    def test_expired(self):
        past = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1)
        score, status = _deadline_score(past)
        assert score == -100
        assert status == "expired"

    def test_none(self):
        score, status = _deadline_score(None)
        assert score == -10


class TestDataQualityScore:
    def test_all_ok(self):
        assert _data_quality_score(all_positions_ok=True, manual_review_count=0, no_price_count=0, insufficient_count=0) == 20

    def test_manual_review(self):
        assert _data_quality_score(all_positions_ok=False, manual_review_count=2, no_price_count=0, insufficient_count=0) == -10

    def test_no_price(self):
        score = _data_quality_score(all_positions_ok=False, manual_review_count=0, no_price_count=1, insufficient_count=0)
        assert score == -30

    def test_insufficient(self):
        score = _data_quality_score(all_positions_ok=False, manual_review_count=0, no_price_count=0, insufficient_count=1)
        assert score == -40


class TestSupplierQualityScore:
    def test_all_trusted(self):
        assert _supplier_quality_score(all_trusted=True, risky_count=0, unknown_count=0, blocked_used=False) == 10

    def test_blocked(self):
        score = _supplier_quality_score(all_trusted=False, risky_count=0, unknown_count=0, blocked_used=True)
        assert score == -100

    def test_risky(self):
        score = _supplier_quality_score(all_trusted=False, risky_count=1, unknown_count=0, blocked_used=False)
        assert score == -15

    def test_unknown(self):
        score = _supplier_quality_score(all_trusted=False, risky_count=0, unknown_count=2, blocked_used=False)
        assert score == -3


class TestCashEfficiencyScore:
    def test_high_roi(self):
        score, roi = _cash_efficiency_score(profit_after_tax=50000, cash_required=50000)
        assert score == 20
        assert roi == 100.0

    def test_no_cash(self):
        score, roi = _cash_efficiency_score(profit_after_tax=0, cash_required=0)
        assert score == 0.0
        assert roi == 0.0

    def test_negative_roi(self):
        score, roi = _cash_efficiency_score(profit_after_tax=100, cash_required=10000)
        assert score == -10


class TestCompetitionScore:
    def test_many_offers(self):
        score, level, _ = _competition_score(offer_count=10, margin_after_tax_percent=20, deadline_status="active")
        assert level == "high"
        assert score < 0

    def test_few_offers(self):
        score, level, _ = _competition_score(offer_count=1, margin_after_tax_percent=20, deadline_status="active")
        assert level == "low"

    def test_deadline_soon(self):
        score, level, _ = _competition_score(offer_count=5, margin_after_tax_percent=20, deadline_status="deadline_soon")
        assert level == "medium"

    def test_mass_goods_high_margin(self):
        score, level, _ = _competition_score(
            offer_count=3, margin_after_tax_percent=35, deadline_status="active",
            purchase_title="Бумага А4 офисная",
        )
        assert level == "high"


class TestCalculateScore:
    def test_high_score(self):
        future = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=5)
        breakdown = calculate_purchase_score(
            purchase_title="Поставка картриджей",
            submission_deadline=future,
            margin_after_tax_percent=30.0,
            profit_after_tax=80000.0,
            cash_required=100000.0,
            offers=[1, 2, 3],
            all_positions_ok=True,
            manual_review_count=0,
            no_price_count=0,
            insufficient_count=0,
            all_trusted_suppliers=True,
            risky_supplier_count=0,
            unknown_supplier_count=0,
            blocked_supplier_used=False,
            unknown_delivery_count=0,
            manual_force_include_count=0,
            low_relevance_used_count=0,
            overbuy_required_count=0,
            captcha_blocked_count=0,
            needs_manual_tax_review=False,
        )
        assert breakdown.score_total > 30

    def test_low_score(self):
        breakdown = calculate_purchase_score(
            purchase_title="Unknown",
            submission_deadline=datetime.now() - timedelta(hours=1),
            margin_after_tax_percent=5.0,
            profit_after_tax=1000.0,
            cash_required=50000.0,
            offers=[],
            all_positions_ok=False,
            manual_review_count=3,
            no_price_count=1,
            insufficient_count=0,
            all_trusted_suppliers=False,
            risky_supplier_count=2,
            unknown_supplier_count=1,
            blocked_supplier_used=False,
            unknown_delivery_count=2,
            manual_force_include_count=1,
            low_relevance_used_count=0,
            overbuy_required_count=0,
            captcha_blocked_count=0,
            needs_manual_tax_review=True,
        )
        assert breakdown.score_total < 0
