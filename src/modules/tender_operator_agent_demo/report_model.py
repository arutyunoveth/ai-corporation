"""Canonical, renderer-neutral procurement report model.

All customer-facing formats must consume this model.  It deliberately keeps
unknown values explicit and never calculates a total from unit prices.
"""
from __future__ import annotations

from typing import Any
from src.shared.config.settings import get_settings


UNKNOWN = "Данных недостаточно — требуется проверка"


def _quality_gate_status(item: dict[str, Any], name: str, quantity: Any, unit: Any) -> str:
    if item.get("scope_classification_conflict"):
        return "scope_classification_conflict"
    if item.get("procurement_scope_type") in {"works", "services"}:
        return "procurement_scope_mismatch"
    if not item.get("name_source_type") or item.get("name_source_type") == "unresolved":
        return "missing_source_provenance"
    if quantity is None and item.get("quantity_source_path"):
        return "quantity_source_unverified"
    if len(name.split()) <= 3 and not item.get("key_characteristics") and not item.get("characteristics"):
        return "generic_item_name"
    return "valid"


def _procurement_volume_status(items: list[dict[str, Any]], category: str | None) -> tuple[str, str]:
    """Determine volume from row-level evidence; never sum incompatible units."""
    if category not in {"goods", "services", "mixed"}:
        return "not_applicable", "Объём не выражается товарными количествами."
    if not items:
        return "not_specified_in_source", "В доступных документах не найдено товарных позиций с количеством."
    specified = [bool(row.get("quantity") not in (None, "") and row.get("unit_normalized")) for row in items]
    if all(specified):
        return "known", "Каждая извлечённая товарная позиция содержит подтверждённые количество и единицу измерения."
    if any(specified):
        return "partially_known", "Количество и единица подтверждены только для части позиций."
    return "not_specified_in_source", "Количество не зафиксировано в доступных строках источника."


def _format_okpd2_codes(codes: list[dict[str, Any]]) -> list[str]:
    return [f"{item['code']} — {item['name']}" for item in codes]


def _item_rows(preliminary: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    graph_model = preliminary.get("canonical_procurement_model") or {}
    mode = get_settings().source_graph_mode
    if mode not in {"legacy", "shadow", "production"}:
        raise ValueError("AI_CORP_SOURCE_GRAPH_MODE must be legacy, shadow, or production")
    if mode == "production" and not graph_model:
        raise RuntimeError("SOURCE_GRAPH_MODEL_REQUIRED")
    if graph_model:
        source_items = graph_model.get("canonical_items", [])
        if mode == "production" and source_items is None:
            raise RuntimeError("SOURCE_GRAPH_MODEL_REQUIRED")
    else:
        source_items = None
    service_items = preliminary.get("service_items") or []
    supply_items = preliminary.get("supply_items") or []
    spec_rows = preliminary.get("spec_table", {}).get("rows", [])
    if source_items is None:
        if mode == "production":
            raise RuntimeError("LEGACY_ITEM_PATH_USED_IN_PRODUCTION")
        source_items = (
            max((service_items, supply_items, spec_rows), key=len)
            if preliminary.get("procurement_kind") == "services"
            else supply_items or service_items or spec_rows
        )
    for sequence, item in enumerate(source_items, start=1):
        official_name = item.get("official_name") or item.get("original_name") or item.get("name") or item.get("Наименование") or UNKNOWN
        if official_name == UNKNOWN:
            continue
        name = item.get("display_name") or official_name
        quantity = item.get("quantity")
        if quantity is None:
            quantity = item.get("Кол-во") if item.get("Кол-во") not in (None, "не указано") else None
        unit = item.get("unit") or item.get("unit_original") or item.get("Ед. изм.")
        evidence_ids = item.get("evidence_ids", [])
        if not evidence_ids and item.get("evidence_id"):
            evidence_ids = [item["evidence_id"]]
        rows.append({
            "stable_item_id": item.get("canonical_item_id") or item.get("stable_item_id") or item.get("evidence_id") or f"line-{sequence}",
            "sequence": sequence,
            "official_name": official_name,
            "display_name": name,
            "original_name": name,
            "normalized_name": item.get("normalized_name") or item.get("name") or name,
            "unit_original": unit or UNKNOWN,
            "unit_normalized": unit,
            "quantity": quantity,
            "quantity_status": item.get("quantity_status") or ("specified" if quantity is not None and unit else "not_specified"),
            "quantity_display": "Не указан документацией" if quantity is None else str(quantity),
            "unit_price": item.get("unit_price"),
            "currency": item.get("currency") or "RUB",
            "pricing_basis": item.get("pricing_basis") or "unknown",
            "line_total": item.get("total_price"),
            "line_total_display": "Не рассчитывается",
            "evidence_ids": evidence_ids,
            "source_document_id": item.get("source_document") or (item.get("Источник") or None),
            "source_row": item.get("source_row_number") or item.get("source_row"),
            "warnings": item.get("warnings", []),
            "field_issues": item.get("field_issues", []),
            "name_source_type": item.get("name_source_type", "unresolved"),
            "name_source_path": item.get("name_source_path"),
            "quantity_source_path": item.get("quantity_source_path"),
            "unit_source_path": item.get("unit_source_path"),
            "source_record_id": item.get("source_record_id"),
            "extraction_strategy": item.get("extraction_strategy"),
            "field_provenance": item.get("field_provenance", {}),
            "characteristics": item.get("characteristics", []),
            "quality_gate_status": _quality_gate_status(item, str(official_name), quantity, unit),
        })
    return rows


def build_procurement_report_model(metadata: dict[str, Any], outputs: dict[str, dict[str, Any]], *, repository_sha: str = "unknown") -> dict[str, Any]:
    requirements = outputs["requirements"]
    preliminary = requirements.get("preliminary_analysis", {})
    canonical_graph = preliminary.get("canonical_procurement_model") or {}
    context = requirements.get("analysis_context", {})
    recommendation = outputs["final_recommendation"]
    risks = outputs["contract_risks"].get("risks", [])
    economics = outputs["economics"]
    items = _item_rows(preliminary)
    scope = context.get("procurement_scope", {})
    if scope.get("scope_classification_conflict"):
        for row in items:
            row["quality_gate_status"] = "scope_classification_conflict"
    procurement = metadata.get("procurement") or {}
    volume_status, volume_status_reason = _procurement_volume_status(items, context.get("procurement_category"))
    if scope.get("scope_classification_conflict"):
        volume_status, volume_status_reason = "scope_conflict", "Тип закупки определён неоднозначно. Товарная часть требует проверки."
    raw_okpd2 = context.get("okpd2_codes") or metadata.get("okpd2_codes") or procurement.get("okpd2_codes", [])
    okpd2_codes = [dict(item, evidence_ids=item.get("evidence_ids") or ["eis_notice:okpd2_codes"]) for item in raw_okpd2 if item.get("code")]
    needs_review_reasons = [reason for reason in recommendation.get("rationale", []) if "неизвестен фактический объём" not in reason.lower()]
    if volume_status != "known":
        needs_review_reasons.append("Неизвестен фактический объём")
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
    subject = context.get("procurement_subject") or metadata.get("procurement_title") or procurement.get("procurement_subject") or metadata.get("tender_title") or UNKNOWN
    nmck = context.get("nmck") or (metadata.get("procurement") or {}).get("initial_price")
    publication_datetime = metadata.get("publication_date") or procurement.get("publication_date")
    application_deadline = metadata.get("deadline") or procurement.get("deadline")
    currency = context.get("currency", "RUB")
    customer_name = context.get("customer_name") or metadata.get("customer_name") or procurement.get("customer_name") or UNKNOWN
    delivery_place = context.get("delivery_place") or metadata.get("delivery_place") or procurement.get("delivery_place") or UNKNOWN
    contract_draft_status = context.get("contract_draft_status") or ("absent" if missing_contract else "unknown")
    coverage = preliminary.get("item_coverage", {})
    economics_lines = [f"{item.get('label')}: {item.get('value')}" for item in economics.get("metrics", [])]
    for spec_row in preliminary.get("spec_table", {}).get("rows", []):
        if spec_row.get("Сумма, руб.") not in (None, "", "—"):
            economics_lines.append(f"Сумма по исходной строке: {spec_row['Сумма, руб.']}")
    canonical_run_status = canonical_graph.get("run_status")
    decision = (
        "Требуется ручная проверка перед коммерческим расчётом" if canonical_run_status == "needs_review"
        else "Анализ завершён с подтверждёнными ограничениями источников" if canonical_run_status == "completed_with_warnings"
        else "Анализ завершён"
    )
    return {
        "metadata": {
            "procurement_number": metadata.get("procurement_id"), "report_id": f"report-{metadata.get('run_id')}",
            "report_version": "r1-canonical-v1", "locale": "ru-RU", "source_set_version": "current-run",
            "extraction_version": "r1-b2", "analysis_version": "r1-b3", "repository_sha": repository_sha,
            "document_count": len(metadata.get("files", [])), "service_item_count": len(items),
            "analyzed_item_count": coverage.get("analyzed_item_count", len(items)),
            "decision_status": canonical_run_status or recommendation.get("recommendation", "needs_review"),
            "degraded_mode": metadata.get("analysis_mode") == "fallback_deterministic_adapter",
            "completeness_status": context.get("document_coverage", "partial"),
        },
        "ai_runtime_provenance": metadata.get("ai_runtime_provenance", {}),
        "procurement_number": metadata.get("procurement_id") or UNKNOWN,
        "procurement_title": subject,
        "publication_datetime": publication_datetime or UNKNOWN,
        "application_deadline": application_deadline or UNKNOWN,
        "decision": decision,
        "nmck": nmck if nmck is not None else UNKNOWN,
        "currency": currency,
        "line_items": items,
        "field_evidence": metadata.get("_field_evidence", {}),
        "customer_name": customer_name,
        "customer_inn": context.get("customer_inn") or metadata.get("customer_inn") or procurement.get("customer_inn"),
        "customer_kpp": context.get("customer_kpp") or metadata.get("customer_kpp") or procurement.get("customer_kpp"),
        "delivery_place": delivery_place,
        "delivery_address": context.get("delivery_address") or delivery_place,
        "delivery_region": context.get("delivery_region"),
        "delivery_status": context.get("delivery_status") or "unknown",
        "delivery_evidence_ids": context.get("delivery_evidence_ids", []),
        "contract_draft_status": contract_draft_status,
        "procurement_scope": scope,
        "contract_draft_documents": context.get("contract_draft_documents", []),
        "contract_draft_evidence_ids": context.get("contract_draft_evidence_ids", []),
        "executive_summary": {
            "subject": subject, "nmck": nmck if nmck is not None else UNKNOWN, "currency": currency,
            "service_item_count": len(items), "analyzed_item_count": coverage.get("analyzed_item_count", len(items)),
            "decision": decision,
            "rationale": needs_review_reasons, "blockers": blockers,
            "next_action": (preliminary.get("next_actions") or [UNKNOWN])[0],
            "source_coverage": context.get("document_coverage", "partial"), "overall_confidence": "low" if missing_contract else "medium",
        },
        "document_coverage": {"discovered": len(metadata.get("files", [])), "parsed": len(metadata.get("files", [])), "missing": ["Проект контракта"] if contract_draft_status == "absent" else [], "warnings": context.get("extraction_warnings", []), "impact": "Договорный анализ ограничен" if contract_draft_status in {"absent", "parse_failed", "unknown"} else ""},
        "procurement_passport": {"subject": subject, "title": subject, "publication_datetime": publication_datetime or UNKNOWN, "application_deadline": application_deadline or UNKNOWN, "category": context.get("procurement_category"), "domain": context.get("domain"), "okpd2": "; ".join(_format_okpd2_codes(okpd2_codes)) if okpd2_codes else (context.get("okpd2") or "не указан в доступном извещении"), "nmck": nmck if nmck is not None else UNKNOWN, "currency": currency, "customer": customer_name, "delivery_place": delivery_place, "contract_draft_status": contract_draft_status},
        "okpd2_codes": okpd2_codes,
        "procurement_volume_status": volume_status,
        "volume_status_reason": volume_status_reason,
        "needs_review_reasons": needs_review_reasons,
        "service_catalog": items,
        "requirements": requirements.get("requirements", []),
        "contract_conditions": {"status": contract_draft_status, "unknown_fields": context.get("unknown_contract_terms", []), "reason": "Проект контракта приложен, но автоматически разобрать его не удалось" if contract_draft_status == "parse_failed" else ("Проект контракта отсутствует" if contract_draft_status == "absent" else "Требуется ручная проверка")},
        "timeline": {"value": application_deadline, "status": "known" if application_deadline else "unknown"},
        "economics": {"known_inputs": economics.get("metrics", []), "unknown_inputs": (["себестоимость", "supplier profile"] if volume_status == "known" else ["фактический объём", "себестоимость", "supplier profile"]), "unavailable_calculations": ["выручка", "прибыль", "маржа", "рентабельность"], "warnings": economics.get("warnings", [])},
        "risks": risks,
        "contradictions": [],
        "missing_data": [{"importance": "blocking", "description": "Проект контракта отсутствует", "why_needed": "Без него неизвестны оплата, приемка, штрафы и обеспечение", "required_action": "Получить проект контракта", "decision_effect": "Блокирует безусловное GO"}] if contract_draft_status == "absent" else [],
        "customer_questions": outputs["supplier_questions"].get("questions", []),
        "bid_decision": {"status": "needs_review", "rationale": needs_review_reasons, "blockers": blockers, "conditions": ["Получить проект контракта", "Подтвердить ресурсы и себестоимость"], "assumptions": [], "confidence": "low" if missing_contract else "medium", "next_action": (preliminary.get("next_actions") or [UNKNOWN])[0], "evidence_ids": []},
        "action_plan": preliminary.get("next_actions", []), "evidence_map": evidence_map,
        "limitations": (["Проект контракта приложен, но автоматически разобрать его не удалось"] if contract_draft_status == "parse_failed" else []) + ([] if volume_status == "known" else ["Неизвестен фактический объём"]) + ["Нет supplier profile", "Нет подтверждённой собственной себестоимости", "Прибыль и маржа не рассчитываются"],
        "provenance": {"run_id": metadata.get("run_id"), "source": metadata.get("procurement_source"), "report_model": "canonical", "production_model_hash": canonical_graph.get("production_model_hash")},
        "compatibility_sections": {
            "report_title": "Отчёт по загруженному прогону тендерного агента",
            "notice_number": metadata.get("procurement_id"),
            "procurement_title": subject,
            "publication_datetime": publication_datetime or UNKNOWN,
            "application_deadline": application_deadline or UNKNOWN,
            "line_items": items,
            "positions_count": len(items),
            "source_status": "Документы получены через ЕИС" if metadata.get("procurement_source") else "Документы загружены вручную",
            "preliminary_overview": preliminary.get("overview", []),
            "spec_columns": preliminary.get("spec_table", {}).get("columns", []),
            "spec_rows": preliminary.get("spec_table", {}).get("rows", []),
            "quotes": outputs["quotes_comparison"].get("highlights", []),
            "economics": economics_lines,
            "contract_highlights": preliminary.get("contract_highlights", []),
            "downloaded_files_count": metadata.get("downloaded_files_count", len(metadata.get("files", []))),
            "archive_available": bool(metadata.get("archive_downloaded")),
        },
    }


def canonical_report_to_markdown(model: dict[str, Any]) -> str:
    meta, summary, passport = model["metadata"], model["executive_summary"], model["procurement_passport"]
    lines = [f"# Анализ закупки {meta.get('procurement_number') or ''}", "", f"- Название закупки: {model.get('procurement_title') or summary['subject']}", f"- Номер закупки: {model.get('procurement_number')}", f"- Дата публикации: {model.get('publication_datetime')}", f"- Окончание подачи заявок: {model.get('application_deadline')}", f"- НМЦК: {model.get('nmck')} {model.get('currency')}", f"- Решение: {model.get('decision')}", "", "## Резюме для принятия решения", f"- Предмет: {summary['subject']}", f"- Строк состава закупки: {summary['service_item_count']}/{summary['analyzed_item_count']} проанализировано"]
    lines += [f"- Блокер: {value}" for value in summary["blockers"]] or ["- Блокеры: не выявлены автоматически"]
    lines += ["", "## Паспорт закупки", f"- Категория: {passport.get('category')}", f"- ОКПД2: {passport.get('okpd2')}", "", "## Состав и объём закупки"]
    if not model["line_items"]:
        lines.append("- Позиции и количество не удалось извлечь из доступных документов; требуется проверка первоисточника.")
    for row in model["line_items"]:
        evidence = ", ".join(row["evidence_ids"])
        lines.append(f"- {row['sequence']}. {row['original_name']} | количество: {row['quantity_display']} | единица: {row['unit_original']} | статус количества: {row['quantity_status']} | источник: {row['source_document_id']} строка {row['source_row']} | [{evidence}]")
    lines += ["", "## Недостающие данные"] + [f"- {item['description']}: {item['required_action']}" for item in model["missing_data"]]
    lines += ["", "## Риски"] + [f"- {risk.get('risk')}: {risk.get('impact')}" for risk in model["risks"]]
    lines += ["", "## Вопросы"] + [f"- {question}" for question in model["customer_questions"]]
    lines += ["", "## Evidence map"] + [f"- [{item['evidence_id']}] {item['document']}, строка {item['row']}: {item['short_excerpt']}" for item in model["evidence_map"]]
    lines += ["", "## Ограничения анализа"] + [f"- {item}" for item in model["limitations"]]
    return "\n".join(lines)
