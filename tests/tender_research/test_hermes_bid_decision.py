from __future__ import annotations

from src.modules.hermes_agent.bid_decision import (
    calculate_supplier_readiness_score,
    determine_bid_decision,
)
from src.modules.hermes_agent.risk_classifier import classify_supplier_risks
from src.modules.hermes_agent.schemas import (
    HermesLineItem,
    HermesQualityCheck,
    HermesRuntimeAnalysisResult,
    HermesSummary,
    NmckMappingItem,
    NmckMappingResult,
    NormalizedLineItem,
    SupplierReadinessMemo,
    SupplierRisk,
)
from src.modules.hermes_agent.supplier_readiness import build_supplier_readiness_memo


def _make_base_result(**overrides) -> HermesRuntimeAnalysisResult:
    data = HermesRuntimeAnalysisResult(
        tender_id="test",
        summary=HermesSummary(subject="Test procurement"),
        line_items=[
            HermesLineItem(name="Item 1", quantity="10", unit="pc"),
            HermesLineItem(name="Item 2", quantity="20", unit="pc"),
        ],
        normalized_line_items=[
            NormalizedLineItem(raw_name="Item 1", normalized_name="Item 1"),
            NormalizedLineItem(raw_name="Item 2", normalized_name="Item 2"),
        ],
        nmck_mapping=NmckMappingResult(
            total_nmck_lines=2, mapped_count=2, unmapped_count=0,
            mapping_status="complete",
            items=[
                NmckMappingItem(line_item_index=0, line_item_name="Item 1", nmck_index=0,
                                nmck_name="Item 1", nmck_price="100", match_score=1.0, match_method="fuzzy"),
                NmckMappingItem(line_item_index=1, line_item_name="Item 2", nmck_index=1,
                                nmck_name="Item 2", nmck_price="200", match_score=1.0, match_method="fuzzy"),
            ],
        ),
        quality_checks=[HermesQualityCheck(check_name="line_items_required_for_goods", status="passed")],
        evidence_coverage_pct=100.0,
    )
    for k, v in overrides.items():
        setattr(data, k, v)
    return data


# =============================================================================
# Risk classifier tests
# =============================================================================


def test_risk_classifier_commercial_risk_partial_mapping():
    result = _make_base_result(
        nmck_mapping=NmckMappingResult(
            total_nmck_lines=2, mapped_count=1, unmapped_count=1,
            mapping_status="partial",
            items=[
                NmckMappingItem(line_item_index=0, line_item_name="Item 1", nmck_index=0,
                                nmck_name="Item 1", nmck_price="100", match_score=1.0, match_method="fuzzy"),
            ],
        ),
    )
    risks = classify_supplier_risks(result)
    commercial = [r for r in risks if r.risk_type == "commercial"]
    assert any("неполный" in r.title or "partial" in r.description for r in commercial)


def test_risk_classifier_commercial_no_nmck():
    result = _make_base_result(
        nmck_mapping=NmckMappingResult(mapping_status="no_nmck_data"),
    )
    risks = classify_supplier_risks(result)
    commercial = [r for r in risks if r.risk_type == "commercial"]
    assert any("НМЦК" in r.title for r in commercial)


def test_risk_classifier_technical_missing_section():
    result = _make_base_result(
        normalized_line_items=[
            NormalizedLineItem(raw_name="Кабель ВВГ 3х1.5", normalized_name="ВВГ",
                               type_mark="ВВГ", cores_count=3, cross_section_mm2=None),
        ],
    )
    risks = classify_supplier_risks(result)
    technical = [r for r in risks if r.risk_type == "technical"]
    assert any("сечение" in r.title.lower() for r in technical)


def test_risk_classifier_contract_short_term():
    result = _make_base_result()
    result.summary.delivery_term = "30 дней с момента подписания"
    risks = classify_supplier_risks(result)
    contract = [r for r in risks if r.risk_type == "contract"]
    assert any("коротк" in r.title.lower() or "срок" in r.title.lower() for r in contract)


def test_risk_classifier_compliance_certificate():
    from src.modules.hermes_agent.schemas import HermesCertificationRequirement
    result = _make_base_result(
        certification_requirements=[
            HermesCertificationRequirement(requirement="Сертификат соответствия",
                                            source_document="tz.pdf", source_quote="требуется сертификат",
                                            confidence=0.9),
        ],
    )
    risks = classify_supplier_risks(result)
    compliance = [r for r in risks if r.risk_type == "compliance"]
    assert len(compliance) > 0


# =============================================================================
# Scoring tests
# =============================================================================


def test_score_starts_high():
    result = _make_base_result()
    memo = build_supplier_readiness_memo(result)
    assert memo.supplier_readiness_score >= 75


def test_score_drops_with_failed_gates():
    result = _make_base_result(
        quality_checks=[
            HermesQualityCheck(check_name="line_items_required_for_goods", status="failed"),
            HermesQualityCheck(check_name="line_items_required_if_specification_exists", status="failed"),
        ],
    )
    memo = build_supplier_readiness_memo(result)
    assert memo.supplier_readiness_score < 75


def test_score_drops_with_blocking_risk():
    result = _make_base_result()
    memo = build_supplier_readiness_memo(result)
    memo.blocking_risks = [
        SupplierRisk(risk_type="compliance", severity="blocking",
                     title="Блокирующий риск", description="test", mitigation=""),
    ]
    score = calculate_supplier_readiness_score(memo, result)
    assert score <= 60


def test_score_low_evidence():
    result = _make_base_result(evidence_coverage_pct=30.0)
    memo = build_supplier_readiness_memo(result)
    assert memo.supplier_readiness_score <= 80


# =============================================================================
# Decision tests
# =============================================================================


def test_go_when_high_score_no_blocks():
    result = _make_base_result(
        quality_checks=[HermesQualityCheck(check_name="line_items_required_for_goods", status="passed")],
        evidence_coverage_pct=100.0,
    )
    memo = build_supplier_readiness_memo(result)
    memo.missing_supplier_data = []
    memo.supplier_readiness_score = calculate_supplier_readiness_score(memo, result)
    decision, _ = determine_bid_decision(memo, result)
    assert decision == "go"


def test_needs_review_medium_score():
    result = _make_base_result(
        line_items=[],
        quality_checks=[HermesQualityCheck(check_name="line_items_required_for_goods", status="failed")],
        evidence_coverage_pct=30.0,
    )
    memo = build_supplier_readiness_memo(result)
    assert memo.bid_decision in ("needs_review", "no_go")


def test_no_go_with_blocking_risk():
    result = _make_base_result()
    memo = build_supplier_readiness_memo(result)
    memo.blocking_risks = [
        SupplierRisk(risk_type="compliance", severity="blocking",
                     title="Блокирующий риск", description="test", mitigation=""),
    ]
    memo.supplier_readiness_score = calculate_supplier_readiness_score(memo, result)
    decision, _ = determine_bid_decision(memo, result)
    assert decision == "no_go"


def test_needs_review_no_prices():
    result = HermesRuntimeAnalysisResult(
        tender_id="test",
        summary=HermesSummary(subject="Test procurement"),
        line_items=[
            HermesLineItem(name="Item 1", quantity="10", unit="pc"),
            HermesLineItem(name="Item 2", quantity="20", unit="pc"),
        ],
        normalized_line_items=[
            NormalizedLineItem(raw_name="Item 1", normalized_name="Item 1"),
            NormalizedLineItem(raw_name="Item 2", normalized_name="Item 2"),
        ],
        nmck_mapping=NmckMappingResult(mapping_status="no_nmck_data"),
        quality_checks=[HermesQualityCheck(check_name="line_items_required_for_goods", status="passed")],
        evidence_coverage_pct=80.0,
    )
    memo = build_supplier_readiness_memo(result)
    assert memo.bid_decision == "needs_review"


# =============================================================================
# Fixture 0142300008526000054 test
# =============================================================================


def test_fixture_0142300008526000054_supplier_readiness():
    result = HermesRuntimeAnalysisResult(
        tender_id="0142300008526000054",
        document_roles=["specification", "nmck_calculation"],
        summary=HermesSummary(
            subject="Поставка кабельной продукции",
            customer="МУП г. Кинель",
            nmck="1500000.0",
            delivery_address="Самарская область, г. Кинель",
            delivery_term="31.12.2026",
        ),
        line_items=[
            HermesLineItem(name="АВВГ-П", quantity="200", unit="м",
                           source_document="specification.pdf", source_quote="АВВГ-П 2х2.5, 200м",
                           standards=["ГОСТ 31996-2012"], confidence=0.9),
            HermesLineItem(name="СИП-4", quantity="1300", unit="м",
                           source_document="specification.pdf", source_quote="СИП-4 2х16, 1300м",
                           confidence=0.9),
            HermesLineItem(name="СИП-4", quantity="700", unit="м",
                           source_document="specification.pdf", source_quote="СИП-4 4х16, 700м",
                           confidence=0.9),
        ],
        normalized_line_items=[
            NormalizedLineItem(raw_name="АВВГ-П", normalized_name="АВВГ",
                               type_mark="АВВГ", cores_count=2, cross_section_mm2=2.5,
                               standard="ГОСТ 31996-2012"),
            NormalizedLineItem(raw_name="СИП-4 2х16", normalized_name="СИП / 2x16.0",
                               type_mark="СИП", cores_count=2, cross_section_mm2=16.0),
            NormalizedLineItem(raw_name="СИП-4 4х16", normalized_name="СИП / 4x16.0",
                               type_mark="СИП", cores_count=4, cross_section_mm2=16.0),
        ],
        nmck_mapping=NmckMappingResult(
            total_nmck_lines=3, mapped_count=3, unmapped_count=0,
            mapping_status="complete",
            items=[
                NmckMappingItem(line_item_index=0, line_item_name="АВВГ-П", nmck_index=0,
                                nmck_name="АВВГ-П", nmck_price="50.00", match_score=1.0, match_method="fuzzy"),
                NmckMappingItem(line_item_index=1, line_item_name="СИП-4 2х16", nmck_index=1,
                                nmck_name="СИП-4 2х16", nmck_price="120.00", match_score=1.0, match_method="fuzzy"),
                NmckMappingItem(line_item_index=2, line_item_name="СИП-4 4х16", nmck_index=2,
                                nmck_name="СИП-4 4х16", nmck_price="180.00", match_score=1.0, match_method="fuzzy"),
            ],
        ),
        quality_checks=[
            HermesQualityCheck(check_name="line_items_required_for_goods", status="passed"),
        ],
        evidence_coverage_pct=85.0,
        procurement_category="electrical_goods",
        category_label="Электротехническая продукция",
    )
    memo = build_supplier_readiness_memo(result)
    assert memo is not None
    assert len(memo.rfq_requirements) == 3
    assert memo.bid_decision == "needs_review"

    missing_fields = [m.field for m in memo.missing_supplier_data]
    assert "stock_availability" in missing_fields

    assert len(memo.next_actions) > 0
