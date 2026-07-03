import json
from pathlib import Path

from src.modules.tender_operator_review.service import (
    build_human_review_checklist_markdown,
    build_human_review_pack,
    build_operator_decision_form_markdown,
    update_run_summary_with_human_review,
)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_human_review_pack_aggregates_tkp_risk_economics_and_bid_flags(tmp_path: Path):
    _write_json(
        tmp_path / "requirements.json",
        {
            "technical_requirements": ["Requirement A"],
            "llm_control": {
                "sections": {
                    "requirements": {
                        "input_redaction": {
                            "redaction_applied": True,
                            "input_chars_before": 200,
                            "input_chars_after": 150,
                        }
                    }
                }
            },
        },
    )
    _write_json(tmp_path / "supplier_questions.json", [{"question": "Question A", "category": "price"}])
    _write(tmp_path / "rfq_request_draft.md", "# RFQ\nManual review required")
    _write(
        tmp_path / "calibrated_contract_risk_memo.md",
        "\n".join(
            [
                "# Calibrated Contract Risk Memo",
                "### [DEAL-BREAKER] Missing mandatory license",
                "- **Risk**: License is missing.",
                "- **Classification**: deal_breaker_candidate",
                "- **Impact**: Cannot proceed.",
                "- **Mitigation**: Escalate.",
                "- **Operator decision required**: True",
                "",
                "### [MATERIAL] Security cost",
                "- **Risk**: Security cost affects margin.",
                "- **Classification**: commercially_material_risk",
                "- **Impact**: Price up.",
                "- **Mitigation**: Reprice.",
                "- **Operator decision required**: True",
            ]
        ),
    )
    _write_json(
        tmp_path / "tkp_normalized_quotes.json",
        [
            {
                "supplier_label": "Supplier A",
                "supplier_id": None,
                "source_file": "/tmp/supplier_a.md",
                "normalization_status": "needs_review",
                "quote_date": None,
                "valid_until": None,
                "currency_code": "RUB",
                "vat_included": None,
                "vat_rate": None,
                "total_amount": 100000.0,
                "total_amount_without_vat": None,
                "delivery_cost": None,
                "delivery_time_days": None,
                "payment_terms": None,
                "warranty_months": None,
                "availability": None,
                "includes_delivery": None,
                "includes_installation": None,
                "certificates_available": None,
                "contact_email": None,
                "contact_phone": None,
                "line_items": [],
                "extraction_confidence": 0.44,
                "fields_needing_review": ["supplier_id", "payment_terms"],
                "warnings": ["vat_unknown"],
                "parser_mode": "deterministic",
                "human_review_required": True,
            },
            {
                "supplier_label": "Supplier B",
                "supplier_id": None,
                "source_file": "/tmp/supplier_b.pdf",
                "normalization_status": "unsupported_format",
                "quote_date": None,
                "valid_until": None,
                "currency_code": "RUB",
                "vat_included": None,
                "vat_rate": None,
                "total_amount": None,
                "total_amount_without_vat": None,
                "delivery_cost": None,
                "delivery_time_days": None,
                "payment_terms": None,
                "warranty_months": None,
                "availability": None,
                "includes_delivery": None,
                "includes_installation": None,
                "certificates_available": None,
                "contact_email": None,
                "contact_phone": None,
                "line_items": [],
                "extraction_confidence": 0.0,
                "fields_needing_review": ["supplier_id"],
                "warnings": ["requires_manual_text_extract"],
                "parser_mode": "deterministic",
                "human_review_required": True,
            },
        ],
    )
    _write_json(
        tmp_path / "tkp_comparison.json",
        {
            "status": "needs_review",
            "suppliers": [{"supplier_label": "Supplier A"}],
        },
    )
    _write_json(
        tmp_path / "economics_summary.json",
        {
            "economics_status": "needs_operator_review",
            "status": "preliminary",
            "lowest_price": 100000.0,
        },
    )
    _write(tmp_path / "bid_decision_recommendation.md", "# Bid Decision Recommendation\nNEEDS_REVIEW")
    _write_json(
        tmp_path / "run_summary.json",
        {
            "bid_decision": {"recommendation": "NEEDS_REVIEW"},
            "supplier_sourcing": {
                "manual_candidates_file_found": True,
                "top_suppliers": [
                    {"display_name": "Supplier A", "inclusion_reason": "score=10; needs review"}
                ],
            },
        },
    )

    pack = build_human_review_pack(tmp_path, operator_id="tender_operator_001", tender_label="tender_001")

    assert pack.blocking_count >= 1
    assert pack.warning_count >= 1
    assert pack.overall_status == "blocked"
    titles = [item.title for item in pack.items]
    assert any("Supplier not matched" in title for title in titles)
    assert any("Low TKP extraction confidence" in title for title in titles)
    assert any("Deal-breaker candidate" in title for title in titles)
    assert any("Economics require operator review" in title for title in titles)

    checklist = build_human_review_checklist_markdown(pack)
    assert "- [ ] проверить НДС" in checklist
    assert "## TKP normalization" in checklist

    decision_form = build_operator_decision_form_markdown(pack)
    assert "# Operator Decision Form" in decision_form
    assert "Approved to prepare bid" in decision_form


def test_update_run_summary_with_human_review_fields(tmp_path: Path):
    _write_json(tmp_path / "run_summary.json", {"pilot_status": "rfq_ready_collect_tkp"})
    _write_json(tmp_path / "requirements.json", {"technical_requirements": ["Requirement A"]})
    _write_json(tmp_path / "supplier_questions.json", [])
    _write(tmp_path / "rfq_request_draft.md", "# RFQ")
    _write(tmp_path / "calibrated_contract_risk_memo.md", "# Calibrated Contract Risk Memo")

    pack = build_human_review_pack(tmp_path, operator_id="op-1", tender_label="tender-x")
    update_run_summary_with_human_review(tmp_path, pack)

    summary = json.loads((tmp_path / "run_summary.json").read_text())
    assert summary["human_review_pack_status"] in {"ready_for_review", "needs_operator_input", "blocked"}
    assert "human_review_blocking_count" in summary
    assert "human_review_warning_count" in summary
    assert "human_review_files" in summary
