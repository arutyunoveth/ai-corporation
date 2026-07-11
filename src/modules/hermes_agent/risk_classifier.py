from __future__ import annotations

import re
from typing import Any

from src.modules.hermes_agent.schemas import (
    HermesRuntimeAnalysisResult,
    SupplierRisk,
)


def classify_supplier_risks(
    result: HermesRuntimeAnalysisResult,
) -> list[SupplierRisk]:
    risks: list[SupplierRisk] = []

    risks.extend(_technical_risks(result))
    risks.extend(_commercial_risks(result))
    risks.extend(_contract_risks(result))
    risks.extend(_compliance_risks(result))
    risks.extend(_delivery_risks(result))

    return risks


def _technical_risks(result: HermesRuntimeAnalysisResult) -> list[SupplierRisk]:
    risks: list[SupplierRisk] = []
    norms = result.normalized_line_items or []

    for i, norm in enumerate(norms):
        raw = norm.raw_name or ""
        is_cable = any(kw in raw.lower() for kw in ("кабель", "провод", "сип"))

        if is_cable and norm.cross_section_mm2 is None:
            risks.append(SupplierRisk(
                risk_type="technical",
                severity="high",
                title=f"Отсутствует сечение для {norm.raw_name}",
                description="Не указано сечение кабеля/провода, невозможно определить точные характеристики.",
                mitigation="Уточнить сечение в документации или запросить у заказчика.",
                confidence=0.8,
            ))

        if is_cable and norm.standard is None:
            risks.append(SupplierRisk(
                risk_type="technical",
                severity="medium",
                title=f"Не указан ГОСТ/ТУ для {norm.raw_name}",
                description="Отсутствие стандарта может привести к несоответствию требованиям.",
                mitigation="Проверить документацию на наличие ГОСТ/ТУ.",
                confidence=0.6,
            ))

        if is_cable and norm.equivalent_allowed is True and norm.type_mark:
            risks.append(SupplierRisk(
                risk_type="technical",
                severity="medium",
                title=f"Эквивалент разрешён для {norm.raw_name}",
                description="Требуется проверка соответствия параметров эквивалента (сечение, материал, напряжение).",
                mitigation="Запросить у заказчика допустимые параметры эквивалента.",
                confidence=0.5,
            ))

    if result.technical_requirements:
        for tr in result.technical_requirements:
            if any(kw in (tr.requirement or "").lower() for kw in ("неоднознач", "уточн", "ориентировоч")):
                risks.append(SupplierRisk(
                    risk_type="technical",
                    severity="high",
                    title="Неоднозначное описание в технических требованиях",
                    description=tr.requirement,
                    mitigation="Запросить уточнение у заказчика.",
                    source_document=tr.source_document,
                    source_quote=tr.source_quote,
                    confidence=tr.confidence,
                ))

    return risks


def _commercial_risks(result: HermesRuntimeAnalysisResult) -> list[SupplierRisk]:
    risks: list[SupplierRisk] = []
    nmck = result.nmck_mapping

    if nmck and nmck.mapping_status == "partial":
        risks.append(SupplierRisk(
            risk_type="commercial",
            severity="high",
            title="НМЦК mapping неполный",
            description=f"{nmck.unmapped_count} позиций не сопоставлены с НМЦК. Невозможно оценить ценовой диапазон.",
            mitigation="Сопоставить оставшиеся позиции с НМЦК вручную или запросить уточнённые данные.",
            confidence=0.9,
        ))

    if nmck and nmck.mapping_status == "no_nmck_data":
        risks.append(SupplierRisk(
            risk_type="commercial",
            severity="medium",
            title="НМЦК не обнаружен",
            description="Нет данных для оценки ценового диапазона и маржинальности.",
            mitigation="Запросить НМЦК у заказчика или провести независимую оценку.",
            confidence=0.8,
        ))

    if not _has_any_supplier_price(result):
        risks.append(SupplierRisk(
            risk_type="commercial",
            severity="high",
            title="Нет цен поставщика",
            description="Отсутствуют цены поставщика на позиции, невозможно рассчитать маржу.",
            mitigation="Запросить коммерческие предложения у поставщиков.",
            confidence=0.9,
        ))

    return risks


def _has_any_supplier_price(result: HermesRuntimeAnalysisResult) -> bool:
    if result.nmck_mapping and result.nmck_mapping.mapped_count > 0:
        for item in result.nmck_mapping.items:
            if item.nmck_price:
                return True
    return False


def _contract_risks(result: HermesRuntimeAnalysisResult) -> list[SupplierRisk]:
    risks: list[SupplierRisk] = []

    delivery_term = (result.summary.delivery_term or "").strip()
    if delivery_term:
        short_term = _is_short_delivery_term(delivery_term)
        if short_term is True:
            risks.append(SupplierRisk(
                risk_type="contract",
                severity="high",
                title="Короткий срок поставки",
                description=f"Срок поставки: {delivery_term}. Возможны сложности с выполнением в срок.",
                mitigation="Проверить наличие товара на складе, оценить логистику.",
                source_document="",
                source_quote=delivery_term,
                confidence=0.6,
            ))
        elif short_term is None:
            risks.append(SupplierRisk(
                risk_type="contract",
                severity="medium",
                title="Срок поставки не указан чётко",
                description=f"Формулировка срока поставки: {delivery_term}.",
                mitigation="Запросить точный срок поставки у заказчика.",
                confidence=0.4,
            ))

    for cr in result.contract_risks:
        severity_map = {"info": "low", "warning": "medium", "critical": "high"}
        risks.append(SupplierRisk(
            risk_type="contract",
            severity=severity_map.get(cr.severity, "medium"),
            title=cr.risk,
            description=cr.risk,
            mitigation="Проверить проект контракта.",
            source_document=cr.source_document,
            source_quote=cr.source_quote,
            confidence=cr.confidence,
        ))

    return risks


def _is_short_delivery_term(term: str) -> bool | None:
    term_lower = term.lower()
    if "заявк" in term_lower or "по заявк" in term_lower:
        return True
    if "поставк" in term_lower and "парти" in term_lower:
        return True
    dates = re.findall(r"(\d{2})[./](\d{2})[./](\d{4})", term)
    if dates:
        return None
    month_pattern = re.findall(r"(\d+)\s*(?:месяц|мес|день|дн|недел)", term_lower)
    if month_pattern:
        for val_str in month_pattern:
            val = int(val_str)
            if val <= 2:
                return True
    return None


def _compliance_risks(result: HermesRuntimeAnalysisResult) -> list[SupplierRisk]:
    risks: list[SupplierRisk] = []

    if result.certification_requirements:
        for cr_idx, cr in enumerate(result.certification_requirements):
            risks.append(SupplierRisk(
                risk_type="compliance",
                severity="medium",
                title=f"Требуется сертификат/декларация: {cr.requirement}",
                description="Для участия необходимо предоставить сертификат или декларацию соответствия.",
                mitigation="Проверить наличие сертификата или запросить у производителя.",
                source_document=cr.source_document,
                source_quote=cr.source_quote,
                confidence=cr.confidence,
            ))

    has_national_regime = False
    for tr in result.technical_requirements:
        tr_lower = (tr.requirement or "").lower()
        if any(kw in tr_lower for kw in ("страна происхождени", "нацрежим", "nr", "запрет", "ограничени", "преимуществ")):
            has_national_regime = True
            risks.append(SupplierRisk(
                risk_type="compliance",
                severity="high",
                title="Ограничения/преимущества по национальному режиму",
                description=tr.requirement,
                mitigation="Проверить соответствие продукции требованиям национального режима.",
                source_document=tr.source_document,
                source_quote=tr.source_quote,
                confidence=tr.confidence,
            ))

    for item in result.line_items:
        for std in item.standards:
            if not has_national_regime:
                cert_needed = any(kw in (std or "").lower() for kw in ("гост", "ту"))
                if cert_needed:
                    risks.append(SupplierRisk(
                        risk_type="compliance",
                        severity="low",
                        title=f"Требуется подтверждение соответствия {std}",
                        description=f"Позиция {item.name} требует подтверждения по стандарту {std}.",
                        mitigation="Предоставить сертификат или декларацию.",
                        source_document=item.source_document,
                        source_quote=item.source_quote,
                        confidence=item.confidence,
                    ))

    return risks


def _delivery_risks(result: HermesRuntimeAnalysisResult) -> list[SupplierRisk]:
    risks: list[SupplierRisk] = []

    addr = (result.summary.delivery_address or "").strip()
    if addr:
        remote_keywords = ("удалён", "отдалён", "север", "камчатк", "сахалин", "магадан", "чукотк", "якути", "таймыр")
        addr_lower = addr.lower()
        if any(kw in addr_lower for kw in remote_keywords):
            risks.append(SupplierRisk(
                risk_type="delivery",
                severity="medium",
                title=f"Удалённый адрес поставки",
                description=f"Адрес поставки: {addr}. Возможны повышенные логистические затраты.",
                mitigation="Рассчитать стоимость доставки, оценить логистические риски.",
                source_document="",
                source_quote=addr,
                confidence=0.5,
            ))

    for risk in result.contract_risks:
        risk_lower = (risk.risk or "").lower()
        if "частичн" in risk_lower and "поставк" in risk_lower:
            risks.append(SupplierRisk(
                risk_type="delivery",
                severity="medium",
                title=risk.risk,
                description="Поставка частями/партиями увеличивает логистические затраты.",
                mitigation="Уточнить график поставки у заказчика.",
                source_document=risk.source_document,
                source_quote=risk.source_quote,
                confidence=risk.confidence,
            ))

    return risks
