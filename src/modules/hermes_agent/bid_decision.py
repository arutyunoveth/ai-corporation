from __future__ import annotations

from src.modules.hermes_agent.schemas import (
    HermesRuntimeAnalysisResult,
    SupplierReadinessMemo,
)


def calculate_supplier_readiness_score(
    memo: SupplierReadinessMemo,
    result: HermesRuntimeAnalysisResult,
) -> int:
    score = 100

    if not result.line_items:
        score -= 40
    elif len(result.line_items) < 3:
        score -= 10

    failed_base_gates = _count_failed_base_gates(result)
    score -= failed_base_gates * 20

    failed_cat_gates = _count_failed_category_gates(result)
    score -= failed_cat_gates * 20

    nmck = result.nmck_mapping
    if nmck:
        if nmck.mapping_status == "no_nmck_data" and result.summary.nmck:
            score -= 15
        elif nmck.mapping_status == "partial":
            score -= 8

    if not _has_any_supplier_price(result):
        score -= 15

    if not _has_stock_confirmation(memo):
        score -= 10

    if memo.blocking_risks:
        score -= 40

    ev = result.evidence_coverage_pct
    if ev < 50:
        score -= 20
    elif ev < 75:
        score -= 10

    return max(0, min(100, score))


def _has_any_supplier_price(result: HermesRuntimeAnalysisResult) -> bool:
    if result.nmck_mapping and result.nmck_mapping.mapped_count > 0:
        for item in result.nmck_mapping.items:
            if item.nmck_price:
                return True
    return False


def _has_stock_confirmation(memo: SupplierReadinessMemo) -> bool:
    for m in memo.missing_supplier_data:
        if m.field in ("stock_availability", "delivery_lead_time"):
            return False
    return True


def _count_failed_base_gates(result: HermesRuntimeAnalysisResult) -> int:
    base_names: set[str] = {
        "line_items_required_for_goods",
        "line_items_required_if_specification_exists",
        "summary_subject_not_too_generic",
        "evidence_required_for_high_confidence",
        "all_documents_used",
    }
    count = 0
    for check in result.quality_checks:
        if check.check_name in base_names and check.status == "failed":
            count += 1
    return count


def _count_failed_category_gates(result: HermesRuntimeAnalysisResult) -> int:
    cat_prefixes = ("electrical_", "category_")
    count = 0
    for check in result.quality_checks:
        if any(check.check_name.startswith(p) for p in cat_prefixes) and check.status == "failed":
            count += 1
    return count


def determine_bid_decision(
    memo: SupplierReadinessMemo,
    result: HermesRuntimeAnalysisResult,
) -> tuple[str, str]:
    score = memo.supplier_readiness_score

    missing_high = [m for m in memo.missing_supplier_data if m.priority == "high"]
    high_risks = [r for r in (memo.technical_risks + memo.commercial_risks + memo.contract_risks) if r.severity == "high"]

    if score >= 75 and not memo.blocking_risks and not high_risks and not missing_high:
        return ("go", "Достаточная готовность для участия в закупке.")

    if memo.blocking_risks:
        reasons = [r.title for r in memo.blocking_risks[:3]]
        return ("no_go", f"Обнаружены блокирующие риски: {'; '.join(reasons)}. Участие не рекомендуется.")

    if score < 40:
        return ("no_go", f"Низкий уровень готовности ({score}/100). Требуется устранение критических пробелов.")

    if high_risks:
        reasons = [r.title for r in high_risks[:3]]
        return ("needs_review", f"Высокие риски: {'; '.join(reasons)}. Требуется анализ.")

    if missing_high:
        fields = [m.field for m in missing_high[:3]]
        return ("needs_review", f"Отсутствуют критические данные поставщика: {', '.join(fields)}.")

    if score < 75:
        return ("needs_review", f"Уровень готовности {score}/100. Требуется дополнительная проверка.")

    return ("needs_review", "Рекомендуется ручная проверка перед принятием решения.")



