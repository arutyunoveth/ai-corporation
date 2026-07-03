from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.modules.tender_operator_review.schemas import HumanReviewItem, HumanReviewPack


SECTION_ORDER = [
    "Tender requirements",
    "Supplier sourcing",
    "RFQ",
    "TKP normalization",
    "Economics",
    "Contract risks",
    "Bid decision",
]

SEVERITY_ORDER = {"blocking": 0, "warning": 1, "info": 2}


def _read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-") or "item"


def _make_item(
    *,
    section: str,
    severity: str,
    title: str,
    description: str,
    source_file: str,
    source_field: str,
    suggested_action: str,
    requires_operator_input: bool = True,
) -> HumanReviewItem:
    token = _slugify(f"{section}-{title}-{source_field}")
    return HumanReviewItem(
        item_id=f"HRI-{token}",
        section=section,
        severity=severity,  # type: ignore[arg-type]
        title=title,
        description=description,
        source_file=source_file,
        source_field=source_field,
        suggested_action=suggested_action,
        requires_operator_input=requires_operator_input,
        resolved=False,
    )


def _maybe_add(items: list[HumanReviewItem], item: HumanReviewItem) -> None:
    if any(existing.item_id == item.item_id for existing in items):
        return
    items.append(item)


def _sort_items(items: list[HumanReviewItem]) -> list[HumanReviewItem]:
    return sorted(
        items,
        key=lambda item: (
            SECTION_ORDER.index(item.section) if item.section in SECTION_ORDER else len(SECTION_ORDER),
            SEVERITY_ORDER.get(item.severity, 9),
            item.title.lower(),
            item.item_id,
        ),
    )


def _build_rfq_items(items: list[HumanReviewItem], output_dir: Path, supplier_questions: list[Any], rfq_draft: str | None) -> None:
    if supplier_questions:
        _maybe_add(
            items,
            _make_item(
                section="RFQ",
                severity="info",
                title="Review supplier questions before outreach",
                description=f"{len(supplier_questions)} supplier questions were generated and require manual validation.",
                source_file=str(output_dir / "supplier_questions.json"),
                source_field="supplier_questions",
                suggested_action="Review question wording, remove duplicates, and confirm commercial/legal wording before contacting suppliers.",
                requires_operator_input=False,
            ),
        )
    if rfq_draft:
        _maybe_add(
            items,
            _make_item(
                section="RFQ",
                severity="info",
                title="Review RFQ draft before sending",
                description="RFQ draft is internal-only until an operator validates addressees, scope, and response requirements.",
                source_file=str(output_dir / "rfq_request_draft.md"),
                source_field="rfq_request_draft",
                suggested_action="Tailor the RFQ draft per supplier and confirm that external sending remains manual.",
                requires_operator_input=True,
            ),
        )


def _build_requirement_items(items: list[HumanReviewItem], output_dir: Path, requirements: dict[str, Any]) -> None:
    if requirements:
        _maybe_add(
            items,
            _make_item(
                section="Tender requirements",
                severity="info",
                title="Review extracted tender requirements",
                description="Tender requirements were generated and should be validated against source documents before supplier outreach.",
                source_file=str(output_dir / "requirements.json"),
                source_field="requirements",
                suggested_action="Confirm technical, qualification, document, and evaluation requirements against the extracted tender text.",
                requires_operator_input=False,
            ),
        )

    llm_control = requirements.get("llm_control", {}) if isinstance(requirements, dict) else {}
    for section_name, section_payload in (llm_control.get("sections") or {}).items():
        input_redaction = section_payload.get("input_redaction") or {}
        if input_redaction.get("redaction_applied"):
            _maybe_add(
                items,
                _make_item(
                    section="Tender requirements",
                    severity="warning",
                    title=f"Cloud redaction applied for {section_name}",
                    description=(
                        f"Input redaction was applied before provider processing "
                        f"({input_redaction.get('input_chars_before')} -> {input_redaction.get('input_chars_after')} chars)."
                    ),
                    source_file=str(output_dir / "requirements.json"),
                    source_field=f"llm_control.sections.{section_name}.input_redaction",
                    suggested_action="Verify that required commercial/legal details were not lost during sanitized cloud processing.",
                ),
            )


def _build_supplier_sourcing_items(items: list[HumanReviewItem], output_dir: Path, run_summary: dict[str, Any]) -> None:
    supplier_sourcing = run_summary.get("supplier_sourcing") or {}
    top_suppliers = supplier_sourcing.get("top_suppliers") or []
    if not top_suppliers:
        _maybe_add(
            items,
            _make_item(
                section="Supplier sourcing",
                severity="warning",
                title="No structured supplier shortlist found",
                description="No top suppliers were recorded in supplier sourcing output.",
                source_file=str(output_dir / "run_summary.json"),
                source_field="supplier_sourcing.top_suppliers",
                suggested_action="Review manual supplier search notes and vendor-list coverage before RFQ outreach.",
            ),
        )
        return

    for supplier in top_suppliers:
        inclusion_reason = str(supplier.get("inclusion_reason") or "")
        if "needs review" in inclusion_reason.lower():
            supplier_name = supplier.get("display_name") or supplier.get("supplier_id") or "supplier"
            _maybe_add(
                items,
                _make_item(
                    section="Supplier sourcing",
                    severity="warning",
                    title=f"Supplier sourcing warning for {supplier_name}",
                    description=f"Shortlist reason indicates manual review: {inclusion_reason}",
                    source_file=str(output_dir / "run_summary.json"),
                    source_field="supplier_sourcing.top_suppliers",
                    suggested_action="Confirm supplier identity, registry quality, and shortlist priority before RFQ distribution.",
                ),
            )


def _build_tkp_items(items: list[HumanReviewItem], output_dir: Path, quotes: list[dict[str, Any]]) -> None:
    for index, quote in enumerate(quotes, start=1):
        supplier_label = quote.get("supplier_label", f"quote_{index}")
        source_field_prefix = f"quotes[{index - 1}]"
        status = quote.get("normalization_status")
        if status in {"failed", "unsupported_format"}:
            _maybe_add(
                items,
                _make_item(
                    section="TKP normalization",
                    severity="blocking",
                    title=f"Unsupported or failed TKP parse for {supplier_label}",
                    description=f"TKP normalization status is '{status}'.",
                    source_file=str(output_dir / "tkp_normalized_quotes.json"),
                    source_field=f"{source_field_prefix}.normalization_status",
                    suggested_action="Provide a supported file or manual text extract and re-run normalization.",
                ),
            )
        if not quote.get("supplier_id"):
            _maybe_add(
                items,
                _make_item(
                    section="TKP normalization",
                    severity="warning",
                    title=f"Supplier not matched for {supplier_label}",
                    description="Normalized TKP could not be confidently matched to Supplier Registry.",
                    source_file=str(output_dir / "tkp_normalized_quotes.json"),
                    source_field=f"{source_field_prefix}.supplier_id",
                    suggested_action="Match the quote to an existing supplier manually before using it for final comparison.",
                ),
            )
        confidence = float(quote.get("extraction_confidence", 0.0) or 0.0)
        if confidence < 0.75:
            _maybe_add(
                items,
                _make_item(
                    section="TKP normalization",
                    severity="warning",
                    title=f"Low TKP extraction confidence for {supplier_label}",
                    description=f"Extraction confidence is {confidence:.2f}.",
                    source_file=str(output_dir / "tkp_normalized_quotes.json"),
                    source_field=f"{source_field_prefix}.extraction_confidence",
                    suggested_action="Open the source TKP and verify key commercial fields before accepting the quote draft.",
                ),
            )
        if quote.get("vat_included") is None and quote.get("vat_rate") is None:
            _maybe_add(
                items,
                _make_item(
                    section="TKP normalization",
                    severity="warning",
                    title=f"VAT not confirmed for {supplier_label}",
                    description="VAT could not be determined from normalized TKP data.",
                    source_file=str(output_dir / "tkp_normalized_quotes.json"),
                    source_field=f"{source_field_prefix}.vat_included",
                    suggested_action="Check the original quote and confirm whether VAT is included and at what rate.",
                ),
            )
        if quote.get("delivery_time_days") is None:
            _maybe_add(
                items,
                _make_item(
                    section="TKP normalization",
                    severity="warning",
                    title=f"Delivery terms missing for {supplier_label}",
                    description="Delivery time was not extracted from the TKP.",
                    source_file=str(output_dir / "tkp_normalized_quotes.json"),
                    source_field=f"{source_field_prefix}.delivery_time_days",
                    suggested_action="Check the source TKP and confirm supplier lead time manually.",
                ),
            )
        if not quote.get("payment_terms"):
            _maybe_add(
                items,
                _make_item(
                    section="TKP normalization",
                    severity="warning",
                    title=f"Payment terms missing for {supplier_label}",
                    description="Payment terms are absent from normalized quote data.",
                    source_file=str(output_dir / "tkp_normalized_quotes.json"),
                    source_field=f"{source_field_prefix}.payment_terms",
                    suggested_action="Confirm payment terms in the source TKP before using quote economics.",
                ),
            )
        for field_name in quote.get("fields_needing_review", []) or []:
            pretty = field_name.replace("_", " ")
            _maybe_add(
                items,
                _make_item(
                    section="TKP normalization",
                    severity="warning",
                    title=f"Review TKP field '{pretty}' for {supplier_label}",
                    description=f"Normalized TKP flagged '{field_name}' for manual review.",
                    source_file=str(output_dir / "tkp_normalized_quotes.json"),
                    source_field=f"{source_field_prefix}.{field_name}",
                    suggested_action="Check the original TKP and fill or correct the flagged field manually.",
                ),
            )


def _build_tkp_comparison_items(items: list[HumanReviewItem], output_dir: Path, tkp_comparison: dict[str, Any] | None) -> None:
    if not tkp_comparison:
        return
    status = tkp_comparison.get("status")
    if status in {"needs_review", "partial", "blocked"}:
        severity = "blocking" if status == "blocked" else "warning"
        _maybe_add(
            items,
            _make_item(
                section="TKP normalization",
                severity=severity,
                title="TKP comparison requires manual review",
                description=f"Comparison status is '{status}'.",
                source_file=str(output_dir / "tkp_comparison.json"),
                source_field="status",
                suggested_action="Review normalized quotes, resolve unsupported fields, and confirm comparison assumptions.",
            ),
        )


def _build_economics_items(items: list[HumanReviewItem], output_dir: Path, economics: dict[str, Any] | None) -> None:
    if not economics:
        return
    economics_status = economics.get("economics_status")
    if economics_status in {"needs_operator_review", "insufficient_data"}:
        severity = "blocking" if economics_status == "insufficient_data" else "warning"
        _maybe_add(
            items,
            _make_item(
                section="Economics",
                severity=severity,
                title="Economics require operator review",
                description=f"Economics status is '{economics_status}'.",
                source_file=str(output_dir / "economics_summary.json"),
                source_field="economics_status",
                suggested_action="Review supplier totals, missing cost assumptions, and confirm whether economics are decision-ready.",
            ),
        )
    if economics.get("status") == "blocked":
        _maybe_add(
            items,
            _make_item(
                section="Economics",
                severity="blocking",
                title="Economics output is blocked",
                description="Economics summary reported a blocked status.",
                source_file=str(output_dir / "economics_summary.json"),
                source_field="status",
                suggested_action="Resolve missing supplier price data or blocked quote assumptions before continuing.",
            ),
        )


def _parse_contract_risk_memo(risk_memo_text: str) -> list[dict[str, Any]]:
    risks: list[dict[str, Any]] = []
    chunks = risk_memo_text.split("### [")
    for chunk in chunks[1:]:
        header, *rest = chunk.splitlines()
        header_text = header.strip()
        clause = header_text.split("]", 1)[1].strip() if "]" in header_text else header_text
        body = "\n".join(rest)
        classification_match = re.search(r"\*\*Classification\*\*:\s*([^\n]+)", body)
        operator_match = re.search(r"\*\*Operator decision required\*\*:\s*([^\n]+)", body, re.IGNORECASE)
        description_match = re.search(r"\*\*Risk\*\*:\s*([^\n]+)", body)
        risks.append(
            {
                "clause": clause,
                "classification": classification_match.group(1).strip() if classification_match else "unknown",
                "operator_decision_required": (operator_match.group(1).strip().lower() == "true") if operator_match else False,
                "description": description_match.group(1).strip() if description_match else "",
            }
        )
    return risks


def _build_contract_risk_items(items: list[HumanReviewItem], output_dir: Path, risk_memo_text: str | None) -> None:
    if not risk_memo_text:
        return
    for index, risk in enumerate(_parse_contract_risk_memo(risk_memo_text), start=1):
        clause = risk.get("clause") or f"risk_{index}"
        if risk.get("classification") == "deal_breaker_candidate":
            _maybe_add(
                items,
                _make_item(
                    section="Contract risks",
                    severity="blocking",
                    title=f"Deal-breaker candidate: {clause}",
                    description=risk.get("description") or "Contract risk was classified as a deal-breaker candidate.",
                    source_file=str(output_dir / "calibrated_contract_risk_memo.md"),
                    source_field=f"risk[{index - 1}].classification",
                    suggested_action="Escalate this clause before proceeding with bid preparation or supplier commitment.",
                ),
            )
        elif risk.get("operator_decision_required"):
            _maybe_add(
                items,
                _make_item(
                    section="Contract risks",
                    severity="warning",
                    title=f"Operator decision required: {clause}",
                    description=risk.get("description") or "Contract clause requires explicit operator judgment.",
                    source_file=str(output_dir / "calibrated_contract_risk_memo.md"),
                    source_field=f"risk[{index - 1}].operator_decision_required",
                    suggested_action="Review the clause and document whether pricing, timeline, or participation decision should change.",
                ),
            )


def _build_bid_decision_items(items: list[HumanReviewItem], output_dir: Path, run_summary: dict[str, Any], bid_decision_md: str | None) -> None:
    bid_decision = run_summary.get("bid_decision") or {}
    recommendation = bid_decision.get("recommendation")
    if recommendation == "NEEDS_REVIEW":
        _maybe_add(
            items,
            _make_item(
                section="Bid decision",
                severity="warning",
                title="Bid decision remains in NEEDS_REVIEW",
                description="Preliminary bid decision has not cleared manual review.",
                source_file=str(output_dir / "run_summary.json"),
                source_field="bid_decision.recommendation",
                suggested_action="Resolve TKP, economics, and contract-risk warnings before final operator approval.",
            ),
        )
    if recommendation == "NO_GO":
        _maybe_add(
            items,
            _make_item(
                section="Bid decision",
                severity="blocking",
                title="Bid decision is NO_GO",
                description="Preliminary recommendation is NO_GO.",
                source_file=str(output_dir / "run_summary.json"),
                source_field="bid_decision.recommendation",
                suggested_action="Escalate and confirm whether the opportunity should be closed.",
            ),
        )
    if bid_decision_md:
        _maybe_add(
            items,
            _make_item(
                section="Bid decision",
                severity="info",
                title="Manual operator approval still required",
                description="Bid decision memo is preliminary and cannot finalize the tender automatically.",
                source_file=str(output_dir / "bid_decision_recommendation.md"),
                source_field="human_review_required",
                suggested_action="Record the final operator decision in the decision form after reviewing all blockers and warnings.",
                requires_operator_input=False,
            ),
        )


def _overall_status(items: list[HumanReviewItem]) -> str:
    blocking_count = len([item for item in items if item.severity == "blocking"])
    if blocking_count:
        return "blocked"
    if any(item.severity == "warning" or item.requires_operator_input for item in items):
        return "needs_operator_input"
    return "ready_for_review"


def build_human_review_pack(output_dir: Path, *, operator_id: str, tender_label: str) -> HumanReviewPack:
    output_dir = output_dir.resolve()
    requirements = _read_json(output_dir / "requirements.json")
    supplier_questions = _read_json(output_dir / "supplier_questions.json")
    run_summary = _read_json(output_dir / "run_summary.json")
    normalized_quotes = _read_json(output_dir / "tkp_normalized_quotes.json")
    tkp_comparison = _read_json(output_dir / "tkp_comparison.json")
    economics = _read_json(output_dir / "economics_summary.json")
    rfq_draft = _read_text(output_dir / "rfq_request_draft.md")
    risk_memo_text = _read_text(output_dir / "calibrated_contract_risk_memo.md")
    bid_decision_md = _read_text(output_dir / "bid_decision_recommendation.md")

    items: list[HumanReviewItem] = []
    _build_requirement_items(items, output_dir, requirements if isinstance(requirements, dict) else {})
    _build_supplier_sourcing_items(items, output_dir, run_summary if isinstance(run_summary, dict) else {})
    _build_rfq_items(items, output_dir, supplier_questions if isinstance(supplier_questions, list) else [], rfq_draft)
    _build_tkp_items(items, output_dir, normalized_quotes if isinstance(normalized_quotes, list) else [])
    _build_tkp_comparison_items(items, output_dir, tkp_comparison if isinstance(tkp_comparison, dict) else None)
    _build_economics_items(items, output_dir, economics if isinstance(economics, dict) else None)
    _build_contract_risk_items(items, output_dir, risk_memo_text)
    _build_bid_decision_items(items, output_dir, run_summary if isinstance(run_summary, dict) else {}, bid_decision_md)

    items = _sort_items(items)
    blocking_count = len([item for item in items if item.severity == "blocking"])
    warning_count = len([item for item in items if item.severity == "warning"])
    info_count = len([item for item in items if item.severity == "info"])
    return HumanReviewPack(
        review_pack_id=f"HRP-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
        tender_label=tender_label,
        operator_id=operator_id,
        generated_at=datetime.now(UTC),
        overall_status=_overall_status(items),  # type: ignore[arg-type]
        blocking_count=blocking_count,
        warning_count=warning_count,
        info_count=info_count,
        items=items,
    )


def build_human_review_checklist_markdown(pack: HumanReviewPack) -> str:
    grouped: dict[str, list[HumanReviewItem]] = defaultdict(list)
    for item in sorted(pack.items, key=lambda item: (SEVERITY_ORDER[item.severity], item.title.lower())):
        grouped[item.section].append(item)

    lines = [
        "# Human Review Checklist",
        "",
        f"- Review pack ID: {pack.review_pack_id}",
        f"- Tender: {pack.tender_label}",
        f"- Operator: {pack.operator_id}",
        f"- Generated: {pack.generated_at.isoformat()}",
        f"- Overall status: {pack.overall_status}",
        f"- Blocking: {pack.blocking_count}",
        f"- Warnings: {pack.warning_count}",
        f"- Info: {pack.info_count}",
        "",
        "## Quick Checks",
        "",
        "- [ ] проверить НДС",
        "- [ ] подтвердить поставщика",
        "- [ ] проверить срок поставки",
        "- [ ] подтвердить финальную цену",
        "",
    ]

    for section in SECTION_ORDER:
        section_items = grouped.get(section, [])
        if not section_items:
            continue
        lines += [f"## {section}", ""]
        for item in sorted(section_items, key=lambda value: (SEVERITY_ORDER[value.severity], value.title.lower())):
            lines.append(f"- [ ] {item.title} ({item.severity})")
            lines.append(f"  Description: {item.description}")
            lines.append(f"  Source: {item.source_file} :: {item.source_field}")
            lines.append(f"  Suggested action: {item.suggested_action}")
        lines += [""]

    return "\n".join(lines)


def build_operator_decision_form_markdown(pack: HumanReviewPack) -> str:
    return "\n".join(
        [
            "# Operator Decision Form",
            "",
            f"Tender: {pack.tender_label}",
            f"Operator: {pack.operator_id}",
            f"Generated: {pack.generated_at.isoformat()}",
            "",
            "## Review result",
            "- [ ] Approved to continue RFQ/TKP collection",
            "- [ ] Approved to prepare bid",
            "- [ ] Needs more supplier data",
            "- [ ] No-go",
            "",
            "## Required corrections",
            "...",
            "",
            "## Final operator notes",
            "...",
            "",
            "## Human approval",
            "Name:",
            "Date:",
            "Signature / confirmation:",
        ]
    )


def update_run_summary_with_human_review(output_dir: Path, pack: HumanReviewPack) -> None:
    summary_path = output_dir / "run_summary.json"
    summary = _read_json(summary_path)
    if not isinstance(summary, dict):
        raise ValueError(f"run_summary.json is missing or invalid at {summary_path}")
    summary["human_review_pack_status"] = pack.overall_status
    summary["human_review_blocking_count"] = pack.blocking_count
    summary["human_review_warning_count"] = pack.warning_count
    summary["human_review_files"] = {
        "pack_json": str(output_dir / "human_review_required.json"),
        "checklist_md": str(output_dir / "human_review_checklist.md"),
        "operator_decision_form_md": str(output_dir / "operator_decision_form.md"),
    }
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
