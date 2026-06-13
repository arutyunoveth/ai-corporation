from __future__ import annotations


def decision_from_score(
    score_total: float,
    risk_level: str,
    has_deadline_expired: bool,
    has_missing_prices: bool,
    blocked_supplier_used: bool,
) -> tuple[str, str]:
    if has_deadline_expired:
        return "reject", "Дедлайн истек."
    if blocked_supplier_used:
        return "reject", "Использован заблокированный поставщик."
    if risk_level == "critical":
        return "reject", "Критический уровень риска."
    if has_missing_prices:
        return "needs_manual_review", "Отсутствуют цены по некоторым позициям."
    if score_total >= 60:
        return "strong_recommend", "Высокий комплексный скоринг."
    if score_total >= 30:
        return "recommend", "Хороший комплексный скоринг."
    if score_total >= 10:
        return "watch", "Средний комплексный скоринг, требует мониторинга."
    if score_total >= -10:
        return "needs_manual_review", "Низкий комплексный скоринг, требуется ручная проверка."
    return "reject", "Отрицательный комплексный скоринг."


def next_action_for_decision(
    decision: str,
    deadline_status: str,
    has_unknown_delivery: bool,
    has_unknown_supplier: bool,
    has_manual_review_items: bool,
) -> str:
    if decision in {"strong_recommend", "recommend"}:
        if has_unknown_delivery:
            return "Уточнить доставку перед подготовкой предложения"
        if has_unknown_supplier:
            return "Проверить поставщиков перед подготовкой предложения"
        if has_manual_review_items:
            return "Проверить позиции с ручной оценкой"
        return "Подготовить коммерческое предложение"
    if decision == "watch":
        return "Мониторить до дедлайна"
    if decision == "needs_manual_review" and deadline_status == "deadline_soon":
        return "Срочная ручная проверка: дедлайн скоро"
    if decision == "needs_manual_review":
        return "Ручная проверка"
    return "Отклонить"
