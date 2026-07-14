"""Canonical, renderer-neutral procurement report model.

All customer-facing formats must consume this model.  It deliberately keeps
unknown values explicit and never calculates a total from unit prices.
"""
from __future__ import annotations

from typing import Any


UNKNOWN = "Данных недостаточно — требуется проверка"


def _item_rows(preliminary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for sequence, item in enumerate(preliminary.get("service_items", []), start=1):
        rows.append({
            "stable_item_id": item.get("stable_item_id"),
            "sequence": sequence,
            "original_name": item.get("original_name") or UNKNOWN,
            "normalized_name": item.get("normalized_name"),
            "unit_original": item.get("unit") or UNKNOWN,
            "unit_normalized": item.get("unit"),
            "quantity": item.get("quantity"),
            "quantity_status": item.get("quantity_status") or "unknown",
            "quantity_display": "Не указан документацией" if item.get("quantity") is None else str(item["quantity"]),
            "unit_price": item.get("unit_price"),
            "currency": "RUB",
            "pricing_basis": item.get("pricing_basis") or "unknown",
            "line_total": None,
            "line_total_display": "Не рассчитывается",
            "evidence_ids": item.get("evidence_ids", []),
            "source_document_id": item.get("source_document"),
            "source_row": item.get("source_row_number"),
            "warnings": [],
        })
    return rows


def build_procurement_report_model(metadata: dict[str, Any], outputs: dict[str, dict[str, Any]], *, repository_sha: str = "unknown") -> dict[str, Any]:
    requirements = outputs["requirements"]
    preliminary = requirements.get("preliminary_analysis", {})
    context = requirements.get("analysis_context", {})
    recommendation = outputs["final_recommendation"]
    risks = outputs["contract_risks"].get("risks", [])
    economics = outputs["economics"]
    items = _item_rows(preliminary)
    missing_contract = "draft_contract" in context.get("missing_documents", preliminary.get("missing_documents", []))
    blockers = ["Отсутствует проект контракта"] if missing_contract else []
    evidence_map = [
        {
            "evidence_id": evidence_id,
            "document": row["source_document_id"],
            "row": row["source_row"],
            "short_excerpt": row["original_name"],
            "related_items": [row["stable_item_id"]],
        }
        for row in items for evidence_id in row["evidence_ids"]
    ]
    subject = context.get("procurement_subject") or metadata.get("tender_title") or UNKNOWN
    nmck = context.get("nmck") or (metadata.get("procurement") or {}).get("initial_price")
    coverage = preliminary.get("item_coverage", {})
    return {
        "metadata": {
            "procurement_number": metadata.get("procurement_id"), "report_id": f"report-{metadata.get('run_id')}",
            "report_version": "r1-canonical-v1", "locale": "ru-RU", "source_set_version": "current-run",
            "extraction_version": "r1-b2", "analysis_version": "r1-b3", "repository_sha": repository_sha,
            "document_count": len(metadata.get("files", [])), "service_item_count": len(items),
            "analyzed_item_count": coverage.get("analyzed_item_count", len(items)),
            "decision_status": recommendation.get("recommendation", "needs_review"),
            "degraded_mode": metadata.get("analysis_mode") == "fallback_deterministic_adapter",
            "completeness_status": context.get("document_coverage", "partial"),
        },
        "executive_summary": {
            "subject": subject, "nmck": nmck, "currency": context.get("currency", "RUB"),
            "service_item_count": len(items), "analyzed_item_count": coverage.get("analyzed_item_count", len(items)),
            "decision": "Требуется дополнительная проверка перед решением об участии",
            "rationale": recommendation.get("rationale", []), "blockers": blockers,
            "next_action": (preliminary.get("next_actions") or [UNKNOWN])[0],
            "source_coverage": context.get("document_coverage", "partial"), "overall_confidence": "low" if missing_contract else "medium",
        },
        "document_coverage": {"discovered": len(metadata.get("files", [])), "parsed": len(metadata.get("files", [])), "missing": ["Проект контракта"] if missing_contract else [], "warnings": context.get("extraction_warnings", []), "impact": "Договорный анализ ограничен" if missing_contract else ""},
        "procurement_passport": {"subject": subject, "category": context.get("procurement_category"), "domain": context.get("domain"), "okpd2": context.get("okpd2"), "nmck": nmck, "currency": context.get("currency", "RUB"), "customer": metadata.get("customer_name")},
        "service_catalog": items,
        "requirements": requirements.get("requirements", []),
        "contract_conditions": {"status": "unknown" if missing_contract else "partially_available", "unknown_fields": context.get("unknown_contract_terms", []), "reason": "Проект контракта отсутствует" if missing_contract else "Требуется ручная проверка"},
        "timeline": {"value": metadata.get("deadline"), "status": "known" if metadata.get("deadline") else "unknown"},
        "economics": {"known_inputs": economics.get("metrics", []), "unknown_inputs": ["фактический объём", "себестоимость", "supplier profile"], "unavailable_calculations": ["выручка", "прибыль", "маржа", "рентабельность"], "warnings": economics.get("warnings", [])},
        "risks": risks,
        "contradictions": [],
        "missing_data": [{"importance": "blocking", "description": "Проект контракта отсутствует", "why_needed": "Без него неизвестны оплата, приемка, штрафы и обеспечение", "required_action": "Получить проект контракта", "decision_effect": "Блокирует безусловное GO"}] if missing_contract else [],
        "customer_questions": outputs["supplier_questions"].get("questions", []),
        "bid_decision": {"status": "needs_review", "rationale": recommendation.get("rationale", []), "blockers": blockers, "conditions": ["Получить проект контракта", "Подтвердить ресурсы и себестоимость"], "assumptions": [], "confidence": "low" if missing_contract else "medium", "next_action": (preliminary.get("next_actions") or [UNKNOWN])[0], "evidence_ids": []},
        "action_plan": preliminary.get("next_actions", []), "evidence_map": evidence_map,
        "limitations": ["Отсутствует проект контракта", "Неизвестен фактический объём", "Нет supplier profile", "Нет подтверждённой собственной себестоимости", "Прибыль и маржа не рассчитываются"],
        "provenance": {"run_id": metadata.get("run_id"), "source": metadata.get("procurement_source"), "report_model": "canonical"},
        "compatibility_sections": {
            "report_title": "Отчёт по загруженному прогону тендерного агента",
            "notice_number": metadata.get("procurement_id"),
            "source_status": "Документы получены через ЕИС" if metadata.get("procurement_source") else "Документы загружены вручную",
            "preliminary_overview": preliminary.get("overview", []),
            "spec_columns": preliminary.get("spec_table", {}).get("columns", []),
            "spec_rows": preliminary.get("spec_table", {}).get("rows", []),
            "quotes": outputs["quotes_comparison"].get("highlights", []),
            "economics": [f"{item.get('label')}: {item.get('value')}" for item in economics.get("metrics", [])],
            "contract_highlights": preliminary.get("contract_highlights", []),
            "downloaded_files_count": metadata.get("downloaded_files_count", len(metadata.get("files", []))),
            "archive_available": bool(metadata.get("archive_downloaded")),
        },
    }


def canonical_report_to_markdown(model: dict[str, Any]) -> str:
    meta, summary, passport = model["metadata"], model["executive_summary"], model["procurement_passport"]
    lines = [f"# Анализ закупки {meta.get('procurement_number') or ''}", "", "## Резюме для принятия решения", f"- Предмет: {summary['subject']}", f"- НМЦК (максимальная цена закупки): {summary['nmck']} {summary['currency']}", f"- Строк услуг: {summary['service_item_count']}/{summary['analyzed_item_count']} проанализировано", f"- Решение: {summary['decision']}"]
    lines += [f"- Блокер: {value}" for value in summary["blockers"]] or ["- Блокеры: не выявлены автоматически"]
    lines += ["", "## Паспорт закупки", f"- Категория: {passport.get('category')}", f"- ОКПД2: {passport.get('okpd2')}", "", "## Перечень услуг и единичных расценок"]
    for row in model["service_catalog"]:
        evidence = ", ".join(row["evidence_ids"])
        lines.append(f"- {row['sequence']}. {row['original_name']} | единица: {row['unit_original']} | единичная цена: {row['unit_price']} RUB | объём: {row['quantity_display']} | источник: {row['source_document_id']} строка {row['source_row']} | [{evidence}]")
    lines += ["", "## Недостающие данные"] + [f"- {item['description']}: {item['required_action']}" for item in model["missing_data"]]
    lines += ["", "## Риски"] + [f"- {risk.get('risk')}: {risk.get('impact')}" for risk in model["risks"]]
    lines += ["", "## Вопросы"] + [f"- {question}" for question in model["customer_questions"]]
    lines += ["", "## Evidence map"] + [f"- [{item['evidence_id']}] {item['document']}, строка {item['row']}: {item['short_excerpt']}" for item in model["evidence_map"]]
    lines += ["", "## Ограничения анализа"] + [f"- {item}" for item in model["limitations"]]
    return "\n".join(lines)
