from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.modules.hermes_agent.models import AgentMemory, TenderAnalysisFeedback
from src.modules.hermes_agent.quality import (
    check_all_documents_used,
    check_evidence_required_for_high_confidence,
    check_line_items_required_for_goods,
    check_line_items_required_if_specification_exists,
    check_summary_subject_not_too_generic,
    determine_final_status,
    run_all_quality_gates,
)
from src.modules.hermes_agent.schemas import (
    HermesAnalysisResponse,
    HermesFeedbackCreateRequest,
    HermesFinalRecommendation,
    HermesLineItem,
    HermesQualityCheck,
    HermesSummary,
)
from src.modules.hermes_agent.service import HermesProcurementAnalysisService


# =============================================================================
# Unit tests: quality gates
# =============================================================================


def _empty_analysis() -> HermesAnalysisResponse:
    return HermesAnalysisResponse(
        tender_id="test-1",
        document_roles=[],
        summary=HermesSummary(),
        line_items=[],
    )


def test_line_items_required_for_goods_passes_when_line_items_present():
    analysis = _empty_analysis()
    analysis.line_items = [HermesLineItem(name="Test item", quantity="10", unit="шт.")]
    check = check_line_items_required_for_goods(analysis)
    assert check.status == "passed"


def test_line_items_required_for_goods_fails_when_goods_indicators_no_items():
    analysis = _empty_analysis()
    analysis.summary.subject = "кабель силовой"
    check = check_line_items_required_for_goods(analysis)
    assert check.status == "failed"
    assert "empty" in check.message


def test_line_items_required_for_goods_passes_when_no_indicator():
    analysis = _empty_analysis()
    check = check_line_items_required_for_goods(analysis)
    assert check.status == "passed"


def test_line_items_required_if_specification_exists_fails_when_spec_without_items():
    analysis = _empty_analysis()
    analysis.document_roles = ["technical_specification", "notice"]
    check = check_line_items_required_if_specification_exists(analysis)
    assert check.status == "failed"


def test_line_items_required_if_specification_exists_passes_with_spec_and_items():
    analysis = _empty_analysis()
    analysis.document_roles = ["technical_specification", "notice"]
    analysis.line_items = [HermesLineItem(name="Cable", quantity="100", unit="m")]
    check = check_line_items_required_if_specification_exists(analysis)
    assert check.status == "passed"


def test_summary_subject_not_too_generic_fails_on_generic_subject_no_items():
    analysis = _empty_analysis()
    analysis.summary.subject = "поставка электротехнической продукции"
    check = check_summary_subject_not_too_generic(analysis)
    assert check.status == "failed"


def test_summary_subject_not_too_generic_passes_with_specific_subject():
    analysis = _empty_analysis()
    analysis.summary.subject = "Поставка кабеля АВВГ-П 2х2.5 и СИП-4"
    check = check_summary_subject_not_too_generic(analysis)
    assert check.status == "passed"


def test_summary_subject_not_too_generic_passes_with_items():
    analysis = _empty_analysis()
    analysis.summary.subject = "поставка электротехнической продукции"
    analysis.line_items = [HermesLineItem(name="Cable")]
    check = check_summary_subject_not_too_generic(analysis)
    assert check.status == "passed"


def test_evidence_required_for_high_confidence_fails_on_missing_source():
    analysis = _empty_analysis()
    analysis.line_items = [
        HermesLineItem(name="Cable", quantity="100", unit="m", confidence=0.9)
    ]
    check = check_evidence_required_for_high_confidence(analysis)
    assert check.status == "failed"


def test_evidence_required_for_high_confidence_passes_with_source():
    analysis = _empty_analysis()
    analysis.line_items = [
        HermesLineItem(
            name="Cable",
            quantity="100",
            unit="m",
            confidence=0.9,
            source_document="specification.pdf",
            source_quote="Кабель АВВГ-П 2х2.5, 200 м",
        )
    ]
    check = check_evidence_required_for_high_confidence(analysis)
    assert check.status == "passed"


def test_evidence_low_confidence_no_source_still_passes():
    analysis = _empty_analysis()
    analysis.line_items = [
        HermesLineItem(name="Cable", quantity="100", unit="m", confidence=0.3)
    ]
    check = check_evidence_required_for_high_confidence(analysis)
    assert check.status == "passed"


def test_all_documents_used_warns_on_unused():
    analysis = _empty_analysis()
    analysis.document_roles = ["notice", "specification", "nmck_calculation"]
    analysis.line_items = [
        HermesLineItem(
            name="Cable",
            quantity="100",
            unit="m",
            confidence=0.9,
            source_document="specification",
            source_quote="Cable 100m",
        )
    ]
    check = check_all_documents_used(analysis)
    assert check.status == "warning"
    assert "notice" in check.message or "nmck" in check.message


def test_all_documents_used_passes():
    analysis = _empty_analysis()
    analysis.document_roles = ["specification"]
    analysis.line_items = [
        HermesLineItem(
            name="Cable",
            quantity="100",
            unit="m",
            confidence=0.9,
            source_document="specification",
            source_quote="Cable 100m",
        )
    ]
    check = check_all_documents_used(analysis)
    assert check.status == "passed"


# =============================================================================
# Unit tests: determine_final_status
# =============================================================================


def test_final_status_ready_when_all_gates_pass():
    analysis = _empty_analysis()
    analysis.line_items = [
        HermesLineItem(name="Cable", quantity="100", unit="m", confidence=0.9,
                       source_document="spec", source_quote="Cable 100m")
    ]
    analysis.summary.subject = "Поставка кабельной продукции"
    status, reason = determine_final_status(analysis)
    assert status == "ready"


def test_final_status_needs_review_when_spec_without_items():
    analysis = _empty_analysis()
    analysis.document_roles = ["technical_specification"]
    status, reason = determine_final_status(analysis)
    assert status == "needs_review"
    assert "Specification exists" in reason


def test_final_status_needs_review_when_generic_subject_no_items():
    analysis = _empty_analysis()
    analysis.summary.subject = "поставка электротехнической продукции"
    status, reason = determine_final_status(analysis)
    assert status == "needs_review"


def test_final_status_needs_review_when_extra_docs_without_items():
    analysis = _empty_analysis()
    analysis.document_roles = ["извещение", "specification", "nmck_calculation"]
    analysis.summary.subject = "Тестовая закупка с конкретным описанием"
    analysis.line_items = []
    status, reason = determine_final_status(analysis)
    assert status == "needs_review"


def test_final_status_ready_with_specific_subject_no_spec():
    analysis = _empty_analysis()
    analysis.document_roles = ["notice"]
    analysis.summary.subject = "Поставка кабеля АВВГ-П 2х2.5"
    status, reason = determine_final_status(analysis)
    assert status == "ready"


# =============================================================================
# Unit tests: run_all_quality_gates
# =============================================================================


def test_run_all_quality_gates_returns_checks():
    analysis = _empty_analysis()
    checks = run_all_quality_gates(analysis)
    assert len(checks) >= 4
    for check in checks:
        assert isinstance(check, HermesQualityCheck)
        assert check.check_name


# =============================================================================
# Integration tests: feedback saves as memory
# =============================================================================


def test_feedback_saves_as_memory(session):
    from src.tender_research.models import ProcurementTender
    tender = ProcurementTender(
        source="test",
        external_id="test-feedback-1",
        title="Test Tender for Feedback",
    )
    session.add(tender)
    session.flush()

    service = HermesProcurementAnalysisService(session)
    request = HermesFeedbackCreateRequest(
        tender_id=tender.id,
        field_path="line_items.0.name",
        feedback_type="correction",
        user_comment="Wrong item name, should be АВВГ-П",
        corrected_value_json={"corrected_name": "АВВГ-П 2х2.5"},
    )
    fb = service.save_feedback_as_memory(request)

    assert fb.tender_id == tender.id
    assert fb.field_path == "line_items.0.name"
    assert fb.feedback_type == "correction"

    memory_records = session.query(AgentMemory).filter(
        AgentMemory.source_tender_id == tender.id
    ).all()
    assert len(memory_records) >= 1
    memory = memory_records[0]
    assert memory.memory_type == "feedback_error_case"
    assert memory.scope == "procurement_analysis"
    assert memory.payload_json.get("field_path") == "line_items.0.name"


def test_feedback_creates_eval_case(session):
    from src.tender_research.models import ProcurementTender
    tender = ProcurementTender(
        source="test",
        external_id="test-feedback-eval-1",
        title="Test Tender for Eval Case",
    )
    session.add(tender)
    session.flush()

    service = HermesProcurementAnalysisService(session)
    request = HermesFeedbackCreateRequest(
        tender_id=tender.id,
        field_path="line_items.1.quantity",
        feedback_type="correction",
        user_comment="Wrong quantity",
    )
    fb = service.save_feedback_as_memory(request)
    eval_case = service.create_eval_case_from_feedback(tender.id, fb)

    assert eval_case.tender_id == tender.id
    assert eval_case.fixture_name.startswith("from_feedback_")
    assert eval_case.must_not_include_json is not None
    assert "line_items.1.quantity" in eval_case.must_not_include_json


# =============================================================================
# Integration test: line_items require source_document and source_quote
# =============================================================================


def test_line_items_must_have_source_document_and_quote():
    analysis = _empty_analysis()
    analysis.line_items = [
        HermesLineItem(name="Item without source", quantity="1", unit="pc", confidence=0.9)
    ]
    checks = run_all_quality_gates(analysis)
    evidence_check = [c for c in checks if c.check_name == "evidence_required_for_high_confidence"]
    assert len(evidence_check) == 1
    assert evidence_check[0].status == "failed"


# =============================================================================
# Eval case fixture test
# =============================================================================


def test_eval_case_fixture_exists():
    fixture_path = Path("tests/fixtures/tender_research/hermes_eval_0142300008526000054.json")
    assert fixture_path.exists()
    with open(fixture_path, encoding="utf-8") as f:
        data = json.load(f)
    assert data["tender_number"] == "0142300008526000054"
    assert data["fixture_name"] == "eval_0142300008526000054_cable_supply"
    assert "must_include_json" in data
    assert "must_not_include_json" in data

    must_include = data["must_include_json"]
    line_items = must_include.get("line_items", [])
    assert len(line_items) >= 3

    names = [item["name"] for item in line_items]
    assert any("АВВГ" in n for n in names)
    assert any("СИП-4" in n for n in names)

    delivery_addr = must_include.get("summary.delivery_address", "")
    assert "Самарская область" in delivery_addr
    assert "Кинель" in delivery_addr

    must_not = data["must_not_include_json"]
    subject = must_not.get("summary.subject", "")
    assert "электротехнической продукции" in subject


# =============================================================================
# Test: run_all_quality_gates produces correct statuses
# =============================================================================


def test_all_gates_run():
    analysis = _empty_analysis()
    analysis.document_roles = ["technical_specification"]
    analysis.summary.subject = "поставка"
    analysis.line_items = [
        HermesLineItem(name="Test", confidence=0.9)
    ]
    checks = run_all_quality_gates(analysis)
    check_map = {c.check_name: c.status for c in checks}

    assert "line_items_required_if_specification_exists" in check_map
    assert "summary_subject_not_too_generic" in check_map
    assert "evidence_required_for_high_confidence" in check_map
    assert "all_documents_used" in check_map
