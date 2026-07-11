from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.modules.hermes_agent.bid_decision import (
    calculate_supplier_readiness_score,
    determine_bid_decision,
)
from src.modules.hermes_agent.risk_classifier import classify_supplier_risks
from src.modules.hermes_agent.schemas import (
    HermesRuntimeAnalysisResult,
    NormalizedLineItem,
    QuestionToCustomer,
    RfqRequirement,
    SupplierMissingData,
    SupplierReadinessMemo,
    SupplierRequiredDocument,
    SupplierRisk,
)


def build_supplier_readiness_memo(
    result: HermesRuntimeAnalysisResult,
) -> SupplierReadinessMemo:
    memo = SupplierReadinessMemo(
        tender_id=result.tender_id,
        source_coverage_pct=result.evidence_coverage_pct,
        created_at=datetime.now(timezone.utc).isoformat(),
    )

    memo.required_documents = extract_required_documents(result)
    memo.missing_supplier_data = detect_missing_supplier_data(result)
    memo.rfq_requirements = build_rfq_requirements(result)

    all_risks = classify_supplier_risks(result)
    memo.technical_risks = [r for r in all_risks if r.risk_type == "technical"]
    memo.commercial_risks = [r for r in all_risks if r.risk_type == "commercial"]
    memo.contract_risks = [r for r in all_risks if r.risk_type == "contract"]
    memo.blocking_risks = [r for r in all_risks if r.severity == "blocking"]

    memo.questions_to_customer = build_questions_to_customer(result)

    score = calculate_supplier_readiness_score(memo, result)
    memo.supplier_readiness_score = score
    bid_decision, reason = determine_bid_decision(memo, result)
    memo.bid_decision = bid_decision
    memo.decision_reason = reason

    memo.next_actions = _build_next_actions(memo, result)

    return memo


def extract_required_documents(
    result: HermesRuntimeAnalysisResult,
) -> list[SupplierRequiredDocument]:
    docs: list[SupplierRequiredDocument] = []

    for req in result.certification_requirements:
        docs.append(SupplierRequiredDocument(
            name=req.requirement,
            reason="Требование сертификации из документации",
            source_document=req.source_document,
            source_quote=req.source_quote,
            required=True,
            confidence=req.confidence,
        ))

    seen: set[str] = set()
    for item in result.line_items:
        for std in item.standards:
            if std and std not in seen:
                seen.add(std)
                docs.append(SupplierRequiredDocument(
                    name=f"Сертификат соответствия {std}",
                    reason=f"Требуется для позиции {item.name}",
                    source_document=item.source_document,
                    source_quote=item.source_quote,
                    required=True,
                    confidence=item.confidence,
                ))

    return docs


def detect_missing_supplier_data(
    result: HermesRuntimeAnalysisResult,
) -> list[SupplierMissingData]:
    missing: list[SupplierMissingData] = []

    if not _has_any_known_prices(result):
        missing.append(SupplierMissingData(
            field="supplier_unit_price",
            reason="Нет данных о ценах поставщика на позиции",
            needed_for="Расчёт маржи и коммерческого предложения",
            priority="high",
        ))

    missing.append(SupplierMissingData(
        field="stock_availability",
        reason="Нет подтверждения наличия товара на складе",
        needed_for="Оценка возможности поставки в срок",
        priority="high",
    ))

    if not result.summary.delivery_term:
        missing.append(SupplierMissingData(
            field="delivery_lead_time",
            reason="Не указан срок поставки в документации",
            needed_for="Планирование отгрузки",
            priority="medium",
        ))

    return missing


def _has_any_known_prices(result: HermesRuntimeAnalysisResult) -> bool:
    if result.nmck_mapping and result.nmck_mapping.mapped_count > 0:
        for item in result.nmck_mapping.items:
            if item.nmck_price:
                return True
    return False


def build_rfq_requirements(
    result: HermesRuntimeAnalysisResult,
) -> list[RfqRequirement]:
    reqs: list[RfqRequirement] = []
    normalized = result.normalized_line_items or []

    for i, item in enumerate(result.line_items):
        norm: NormalizedLineItem | None = normalized[i] if i < len(normalized) else None
        chars: list[str] = []
        certs: list[str] = []

        if norm:
            if norm.type_mark:
                chars.append(f"Марка: {norm.type_mark}")
            if norm.cores_count is not None:
                chars.append(f"Количество жил: {norm.cores_count}")
            if norm.cross_section_mm2 is not None:
                chars.append(f"Сечение: {norm.cross_section_mm2} мм²")
            if norm.voltage is not None:
                chars.append(f"Напряжение: {norm.voltage} кВ")
            if norm.conductor_material:
                chars.append(f"Материал проводника: {norm.conductor_material}")
            if norm.insulation_material:
                chars.append(f"Материал изоляции: {norm.insulation_material}")
            if norm.standard:
                chars.append(f"Стандарт: {norm.standard}")
                certs.append(f"Сертификат соответствия {norm.standard}")
            if norm.equivalent_allowed is not None:
                chars.append(f"Эквивалент разрешён: {'да' if norm.equivalent_allowed else 'нет'}")

        for std in item.standards:
            cert_name = f"Сертификат соответствия {std}"
            if cert_name not in certs:
                certs.append(cert_name)

        for tr in result.technical_requirements:
            if tr.requirement and tr.requirement not in chars:
                chars.append(tr.requirement)

        reqs.append(RfqRequirement(
            line_item_ref=item.position_no or str(i + 1),
            normalized_name=norm.normalized_name if norm else item.name,
            quantity=item.quantity,
            unit=item.unit,
            required_characteristics=chars,
            certificates_required=certs,
            delivery_terms=result.summary.delivery_term,
            price_needed=True,
        ))

    return reqs


def build_questions_to_customer(
    result: HermesRuntimeAnalysisResult,
) -> list[QuestionToCustomer]:
    questions: list[QuestionToCustomer] = []
    seen: set[str] = set()

    if not result.summary.delivery_term:
        q = "Каков желаемый срок поставки?"
        if q not in seen:
            seen.add(q)
            questions.append(QuestionToCustomer(
                question=q,
                reason="Срок поставки не указан в документации",
                priority="high",
            ))

    if result.nmck_mapping and result.nmck_mapping.mapping_status == "no_nmck_data":
        q = "Предоставьте расчёт НМЦК для сопоставления с ценами поставщиков."
        if q not in seen:
            seen.add(q)
            questions.append(QuestionToCustomer(
                question=q,
                reason="НМЦК не обнаружен в документации",
                priority="medium",
            ))

    for risk in [r for r in classify_supplier_risks(result) if r.severity == "high"]:
        q_text = risk.mitigation if risk.mitigation else f"Как вы планируете решать: {risk.title}?"
        if q_text not in seen:
            seen.add(q_text)
            questions.append(QuestionToCustomer(
                question=q_text,
                reason=risk.description,
                priority="high",
            ))

    return questions


def _build_next_actions(
    memo: SupplierReadinessMemo,
    result: HermesRuntimeAnalysisResult,
) -> list[str]:
    actions: list[str] = []

    if memo.missing_supplier_data:
        fields = [m.field for m in memo.missing_supplier_data]
        actions.append(f"Запросить у поставщика: {', '.join(fields)}.")

    if memo.rfq_requirements:
        actions.append(f"Сформировать RFQ-запрос по {len(memo.rfq_requirements)} позициям.")

    if memo.questions_to_customer:
        actions.append(f"Направить {len(memo.questions_to_customer)} вопросов заказчику.")

    if memo.blocking_risks:
        actions.append("Устранить блокирующие риски перед принятием решения.")

    if result.nmck_mapping and result.nmck_mapping.mapping_status == "no_nmck_data":
        actions.append("Запросить НМЦК для оценки ценового диапазона.")

    if not actions:
        actions.append("Проверить цены поставщика, подтвердить наличие, подготовить коммерческое предложение.")

    return actions
