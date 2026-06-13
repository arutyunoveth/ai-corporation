from __future__ import annotations

from src.modules.deal_scoring.recommendations import decision_from_score, next_action_for_decision


class TestDecisionFromScore:
    def test_strong_recommend(self):
        decision, reason = decision_from_score(
            score_total=75, risk_level="low",
            has_deadline_expired=False, has_missing_prices=False,
            blocked_supplier_used=False,
        )
        assert decision == "strong_recommend"

    def test_recommend(self):
        decision, _ = decision_from_score(
            score_total=40, risk_level="low",
            has_deadline_expired=False, has_missing_prices=False,
            blocked_supplier_used=False,
        )
        assert decision == "recommend"

    def test_watch(self):
        decision, _ = decision_from_score(
            score_total=15, risk_level="medium",
            has_deadline_expired=False, has_missing_prices=False,
            blocked_supplier_used=False,
        )
        assert decision == "watch"

    def test_needs_manual_review(self):
        decision, _ = decision_from_score(
            score_total=0, risk_level="medium",
            has_deadline_expired=False, has_missing_prices=False,
            blocked_supplier_used=False,
        )
        assert decision == "needs_manual_review"

    def test_reject_low_score(self):
        decision, _ = decision_from_score(
            score_total=-20, risk_level="high",
            has_deadline_expired=False, has_missing_prices=False,
            blocked_supplier_used=False,
        )
        assert decision == "reject"

    def test_reject_expired(self):
        decision, _ = decision_from_score(
            score_total=100, risk_level="low",
            has_deadline_expired=True, has_missing_prices=False,
            blocked_supplier_used=False,
        )
        assert decision == "reject"

    def test_reject_blocked_supplier(self):
        decision, _ = decision_from_score(
            score_total=100, risk_level="low",
            has_deadline_expired=False, has_missing_prices=False,
            blocked_supplier_used=True,
        )
        assert decision == "reject"

    def test_reject_critical_risk(self):
        decision, _ = decision_from_score(
            score_total=100, risk_level="critical",
            has_deadline_expired=False, has_missing_prices=False,
            blocked_supplier_used=False,
        )
        assert decision == "reject"

    def test_needs_manual_review_missing_prices(self):
        decision, _ = decision_from_score(
            score_total=100, risk_level="low",
            has_deadline_expired=False, has_missing_prices=True,
            blocked_supplier_used=False,
        )
        assert decision == "needs_manual_review"


class TestNextAction:
    def test_prepare_offer(self):
        action = next_action_for_decision("strong_recommend", "active", False, False, False)
        assert "Подготовить" in action

    def test_unknown_delivery(self):
        action = next_action_for_decision("recommend", "active", True, False, False)
        assert "доставк" in action

    def test_unknown_supplier(self):
        action = next_action_for_decision("recommend", "active", False, True, False)
        assert "поставщик" in action

    def test_manual_review_items(self):
        action = next_action_for_decision("recommend", "active", False, False, True)
        assert "проверить" in action.lower()

    def test_monitoring(self):
        action = next_action_for_decision("watch", "active", False, False, False)
        assert "Мониторить" in action

    def test_urgent_review(self):
        action = next_action_for_decision("needs_manual_review", "deadline_soon", False, False, False)
        assert "Срочная" in action

    def test_reject(self):
        action = next_action_for_decision("reject", "active", False, False, False)
        assert "Отклонить" in action
