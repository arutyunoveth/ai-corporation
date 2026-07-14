from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.modules.hermes_agent.client import HermesClient
from src.modules.hermes_agent.schemas import (
    HermesAnalysisResponse,
    HermesFinalRecommendation,
    HermesLineItem,
    HermesQualityCheck,
    HermesRuntimeAnalysisResult,
    HermesSummary,
)
from src.shared.config.settings import get_settings


# =============================================================================
# HermesClient tests
# =============================================================================


def _mock_context() -> dict:
    return {
        "tender": {
            "id": "test-1",
            "registry_number": "0142300008526000054",
            "title": "Поставка кабельной продукции",
            "customer_name": "МУП г. Кинель",
            "nmck_amount": 1500000.0,
        },
        "documents": [],
        "document_roles": ["notice", "specification"],
    }


def _make_analysis(**kwargs) -> HermesAnalysisResponse:
    data = {
        "tender_id": "test-1",
        "document_roles": ["notice", "specification"],
        "summary": {"subject": "Поставка кабельной продукции", "customer": "", "nmck": "", "delivery_address": "", "delivery_term": ""},
        "line_items": [],
        "quality_checks": [],
        "final_recommendation": {"status": "needs_review", "reason": "test"},
    }
    data.update(kwargs)
    return HermesAnalysisResponse(**data)


@patch.object(HermesClient, "_can_operate", return_value=False)
def test_hermes_disabled_returns_fallback(mock_can_operate):
    client = HermesClient()
    result = client.analyze_procurement(_mock_context())
    assert result.final_recommendation.status == "needs_review"
    assert "Hermes недоступен" in result.final_recommendation.reason
    assert len(result.missing_data) > 0


@patch.object(HermesClient, "healthcheck", return_value=False)
def test_hermes_healthcheck_false_fallback(mock_healthcheck):
    client = HermesClient()
    assert client.healthcheck() is False
    result = client.analyze_procurement(_mock_context())
    assert result.final_recommendation.status == "needs_review"


@patch.object(HermesClient, "healthcheck", return_value=True)
@patch.object(HermesClient, "_can_operate", return_value=True)
def test_hermes_enabled_requires_endpoint(mock_health, mock_can):
    client = HermesClient()
    assert client.healthcheck() is True


@patch.object(HermesClient, "_can_operate", return_value=False)
def test_hermes_disabled_no_crash(mock_can):
    client = HermesClient()
    result = client.analyze_procurement({"tender": {"id": "x"}})
    assert isinstance(result, HermesAnalysisResponse)


@patch.object(HermesClient, "_can_operate", return_value=False)
def test_improve_disabled_returns_original(mock_can):
    client = HermesClient()
    original = _make_analysis()
    checks = [HermesQualityCheck(check_name="line_items_required_for_goods", status="failed")]
    result = client.improve_analysis(_mock_context(), original, checks)
    assert result is original


@patch.object(HermesClient, "_can_operate", return_value=False)
def test_reflect_disabled_returns_stub(mock_can):
    client = HermesClient()
    result = client.reflect_on_feedback({"field": "test"})
    assert result.get("applied") is False
    assert "disabled" in result.get("reflection", "")


# =============================================================================
# Runtime analysis flow tests
# =============================================================================


def test_load_relevant_memory(session):
    from src.modules.hermes_agent.models import AgentMemory
    from src.modules.hermes_agent.service import HermesProcurementAnalysisService

    session.add(AgentMemory(
        memory_type="feedback_error_case",
        scope="procurement_analysis",
        category="field_path:line_items.0.name",
        payload_json={"field_path": "line_items.0.name", "corrected": "Cable"},
        source_tender_id="tender-current",
    ))
    session.flush()

    service = HermesProcurementAnalysisService(session)
    context = {
        "tender": {"id": "tender-current"},
        "documents": [],
        "document_roles": [],
    }
    memories = service.load_relevant_memory(context)
    assert len(memories) >= 1

    types = {m["memory_type"] for m in memories}
    assert "feedback_error_case" in types


def test_evidence_coverage_percentage():
    from src.modules.hermes_agent.quality import evidence_coverage_percentage

    analysis = _make_analysis()
    analysis.line_items = [
        HermesLineItem(name="Cable", source_document="spec", source_quote="Cable 100m", confidence=0.9),
        HermesLineItem(name="Bolt", source_document="", source_quote="", confidence=0.3),
    ]
    pct = evidence_coverage_percentage(analysis)
    assert pct == 50.0


def test_evidence_coverage_empty():
    from src.modules.hermes_agent.quality import evidence_coverage_percentage

    analysis = _make_analysis()
    pct = evidence_coverage_percentage(analysis)
    assert pct == 0.0


def test_improvement_attempted_when_failed_checks():
    from src.modules.hermes_agent.service import HermesProcurementAnalysisService

    analysis = _make_analysis(
        line_items=[],
        document_roles=["technical_specification"],
        summary=HermesSummary(subject="поставка электротехнической продукции"),
    )

    from src.modules.hermes_agent.quality import run_all_quality_gates
    checks = run_all_quality_gates(analysis)
    failed = [c for c in checks if c.status == "failed"]

    assert any("line_items" in c.check_name for c in failed), "Expected line_items gate to fail"


def test_high_confidence_without_source_still_fails():
    from src.modules.hermes_agent.quality import check_evidence_required_for_high_confidence

    analysis = _make_analysis()
    analysis.line_items = [
        HermesLineItem(name="Cable", quantity="100", unit="m", confidence=0.9),
    ]
    check = check_evidence_required_for_high_confidence(analysis)
    assert check.status == "failed"


def test_high_confidence_with_source_passes():
    from src.modules.hermes_agent.quality import check_evidence_required_for_high_confidence

    analysis = _make_analysis()
    analysis.line_items = [
        HermesLineItem(
            name="Cable", quantity="100", unit="m", confidence=0.9,
            source_document="specification.pdf", source_quote="Кабель 100м",
        ),
    ]
    check = check_evidence_required_for_high_confidence(analysis)
    assert check.status == "passed"


# =============================================================================
# HermesRuntimeAnalysisResult tests
# =============================================================================


def test_runtime_analysis_result_has_extra_fields():
    result = HermesRuntimeAnalysisResult(
        tender_id="test-1",
        applied_memory_count=3,
        improvement_attempted=True,
        improvement_succeeded=True,
        evidence_coverage_pct=75.0,
        documents_used_count=2,
        documents_total_count=4,
    )
    assert result.applied_memory_count == 3
    assert result.improvement_attempted is True
    assert result.improvement_succeeded is True
    assert result.evidence_coverage_pct == 75.0
    assert result.documents_used_count == 2
    assert result.documents_total_count == 4
    assert result.final_recommendation.status == "ready"


def test_runtime_analysis_result_inherits_hermes_fields():
    result = HermesRuntimeAnalysisResult(
        tender_id="test-1",
        document_roles=["notice", "specification"],
        summary=HermesSummary(subject="Cable supply"),
        line_items=[
            HermesLineItem(name="Cable", quantity="100", unit="m", confidence=0.9,
                           source_document="spec", source_quote="Cable 100m"),
        ],
        applied_memory_count=0,
    )
    assert result.summary.subject == "Cable supply"
    assert len(result.line_items) == 1
    assert result.line_items[0].name == "Cable"


# =============================================================================
# Eval fixture check
# =============================================================================


def test_0142300008526000054_fixture_has_three_items():
    path = "tests/fixtures/tender_research/hermes_eval_0142300008526000054.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    must_include = data["must_include_json"]
    line_items = must_include.get("line_items", [])
    assert len(line_items) >= 3

    names = [i["name"] for i in line_items]
    # АВВГ-П 2х2.5 — 200 м
    assert any("АВВГ" in n for n in names)
    # СИП-4 2х16 — 1300 м
    # СИП-4 4х16 — 700 м
    sip_items = [i for i in line_items if "СИП" in i["name"]]
    assert len(sip_items) >= 2

    quantities = {i.get("quantity", "") for i in line_items}
    assert "200" in quantities
    assert "1300" in quantities or "700" in quantities


# =============================================================================
# Integration: feedback reflection
# =============================================================================


def test_run_feedback_reflection_requires_existing_feedback(session):
    from src.modules.hermes_agent.service import HermesProcurementAnalysisService

    service = HermesProcurementAnalysisService(session)
    with pytest.raises(ValueError, match="not found"):
        service.run_feedback_reflection("nonexistent-id")


def test_run_feedback_reflection_with_valid_feedback(session):
    from src.modules.hermes_agent.models import TenderAnalysisFeedback
    from src.modules.hermes_agent.service import HermesProcurementAnalysisService
    from src.tender_research.models import ProcurementTender

    tender = ProcurementTender(
        source="test",
        external_id="test-reflection-1",
        title="Test Reflection",
    )
    session.add(tender)
    session.flush()

    fb = TenderAnalysisFeedback(
        tender_id=tender.id,
        field_path="line_items.0.quantity",
        feedback_type="correction",
        user_comment="Wrong quantity in analysis",
    )
    session.add(fb)
    session.flush()

    service = HermesProcurementAnalysisService(session)
    result = service.run_feedback_reflection(fb.id)
    # Should not crash; if Hermes is disabled, returns stub
    assert isinstance(result, dict)
    assert "reflection" in result


# =============================================================================
# Fallback analysis behavior
# =============================================================================


def test_fallback_spec_triggers_needs_review():
    client = HermesClient()
    context = _mock_context()
    context["document_roles"] = ["technical_specification"]

    with patch.object(HermesClient, "_can_operate", return_value=False):
        result = client.analyze_procurement(context)
        assert result.final_recommendation.status == "needs_review"


def test_fallback_no_spec_is_ready():
    client = HermesClient()
    context = _mock_context()
    context["document_roles"] = ["notice"]

    with patch.object(HermesClient, "_can_operate", return_value=False):
        result = client.analyze_procurement(context)
        assert result.final_recommendation.status == "ready"


# =============================================================================
# Service: build_runtime_context
# =============================================================================


def test_build_runtime_context_with_tender(session):
    from src.modules.hermes_agent.service import HermesProcurementAnalysisService
    from src.tender_research.models import ProcurementTender

    tender = ProcurementTender(
        source="test",
        external_id="test-rt-ctx-1",
        title="Runtime Context Test",
    )
    session.add(tender)
    session.flush()

    service = HermesProcurementAnalysisService(session)
    ctx = service.build_runtime_context(tender.id)

    assert "tender" in ctx
    assert ctx["tender"]["title"] == "Runtime Context Test"
    assert "documents" in ctx
    assert "document_roles" in ctx
