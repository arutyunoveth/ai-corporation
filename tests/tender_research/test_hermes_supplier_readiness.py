from __future__ import annotations

from src.modules.hermes_agent.schemas import (
    HermesAnalysisResponse,
    HermesCertificationRequirement,
    HermesContractRisk,
    HermesFinalRecommendation,
    HermesLineItem,
    HermesQualityCheck,
    HermesRuntimeAnalysisResult,
    HermesSummary,
    HermesTechnicalRequirement,
    NmckLine,
    NmckMappingItem,
    NmckMappingResult,
    NormalizedLineItem,
    SupplierReadinessMemo,
)
from src.modules.hermes_agent.supplier_readiness import (
    build_rfq_requirements,
    build_supplier_readiness_memo,
    build_questions_to_customer,
    detect_missing_supplier_data,
    extract_required_documents,
)


def _make_result(**overrides) -> HermesRuntimeAnalysisResult:
    data = HermesRuntimeAnalysisResult(
        tender_id="test-tender",
        document_roles=["specification", "nmck_calculation"],
        summary=HermesSummary(
            subject="Поставка кабельной продукции",
            customer="МУП г. Кинель",
            nmck="1500000.0",
            delivery_address="Самарская область, г. Кинель",
            delivery_term="31.12.2026",
        ),
        line_items=[
            HermesLineItem(name="Кабель АВВГ-П 2х2.5", quantity="200", unit="м",
                           source_document="specification.pdf", source_quote="АВВГ-П 2х2.5, 200м",
                           standards=["ГОСТ 31996-2012"], confidence=0.9),
            HermesLineItem(name="Кабель СИП-4 2х16", quantity="1300", unit="м",
                           source_document="specification.pdf", source_quote="СИП-4 2х16, 1300м",
                           confidence=0.9),
            HermesLineItem(name="Кабель СИП-4 4х16", quantity="700", unit="м",
                           source_document="specification.pdf", source_quote="СИП-4 4х16, 700м",
                           confidence=0.9),
        ],
        normalized_line_items=[
            NormalizedLineItem(raw_name="Кабель АВВГ-П 2х2.5", normalized_name="АВВГ / 2x2.5",
                               type_mark="АВВГ", cores_count=2, cross_section_mm2=2.5,
                               voltage=0.66, standard="ГОСТ 31996-2012", equivalent_allowed=True),
            NormalizedLineItem(raw_name="Кабель СИП-4 2х16", normalized_name="СИП / 2x16.0",
                               type_mark="СИП", cores_count=2, cross_section_mm2=16.0,
                               voltage=1.0, equivalent_allowed=True),
            NormalizedLineItem(raw_name="Кабель СИП-4 4х16", normalized_name="СИП / 4x16.0",
                               type_mark="СИП", cores_count=4, cross_section_mm2=16.0,
                               voltage=1.0, equivalent_allowed=True),
        ],
        nmck_mapping=NmckMappingResult(
            total_nmck_lines=3,
            mapped_count=3,
            unmapped_count=0,
            mapping_status="complete",
            items=[
                NmckMappingItem(line_item_index=0, line_item_name="Кабель АВВГ-П 2х2.5", nmck_index=0,
                                nmck_name="Кабель АВВГ-П 2х2.5", nmck_price="50.00", match_score=1.0, match_method="fuzzy"),
                NmckMappingItem(line_item_index=1, line_item_name="Кабель СИП-4 2х16", nmck_index=1,
                                nmck_name="Кабель СИП-4 2х16", nmck_price="120.00", match_score=1.0, match_method="fuzzy"),
                NmckMappingItem(line_item_index=2, line_item_name="Кабель СИП-4 4х16", nmck_index=2,
                                nmck_name="Кабель СИП-4 4х16", nmck_price="180.00", match_score=1.0, match_method="fuzzy"),
            ],
        ),
        quality_checks=[
            HermesQualityCheck(check_name="line_items_required_for_goods", status="passed"),
        ],
        evidence_coverage_pct=90.0,
        procurement_category="electrical_goods",
        category_label="Электротехническая продукция",
    )
    for k, v in overrides.items():
        setattr(data, k, v)
    return data


# =============================================================================
# build_rfq_requirements tests
# =============================================================================


def test_build_rfq_requirements_creates_three_reqs():
    result = _make_result()
    reqs = build_rfq_requirements(result)
    assert len(reqs) == 3


def test_rfq_includes_electrical_characteristics():
    result = _make_result()
    reqs = build_rfq_requirements(result)
    abvg = [r for r in reqs if "АВВГ" in r.normalized_name][0]
    chars_text = " ".join(abvg.required_characteristics)
    assert "АВВГ" in chars_text or "АВВГ" in str(abvg.required_characteristics)
    assert "Сечение: 2.5" in str(abvg.required_characteristics)
    assert "Стандарт: ГОСТ 31996-2012" in str(abvg.required_characteristics)


def test_rfq_includes_certificates():
    result = _make_result()
    reqs = build_rfq_requirements(result)
    abvg = [r for r in reqs if "АВВГ" in r.normalized_name][0]
    assert any("ГОСТ 31996-2012" in c for c in abvg.certificates_required)


def test_rfq_price_needed_default():
    result = _make_result()
    reqs = build_rfq_requirements(result)
    for r in reqs:
        assert r.price_needed is True


def test_rfq_delivery_terms():
    result = _make_result()
    reqs = build_rfq_requirements(result)
    for r in reqs:
        assert r.delivery_terms == "31.12.2026"


# =============================================================================
# detect_missing_supplier_data tests
# =============================================================================


def test_missing_supplier_data_includes_prices():
    result = _make_result()
    missing = detect_missing_supplier_data(result)
    fields = [m.field for m in missing]
    assert "supplier_unit_price" not in fields  # has nmck prices


def test_missing_supplier_data_includes_stock():
    result = _make_result()
    missing = detect_missing_supplier_data(result)
    fields = [m.field for m in missing]
    assert "stock_availability" in fields


def test_missing_prices_when_no_nmck_prices():
    result = _make_result()
    result.nmck_mapping = NmckMappingResult(
        total_nmck_lines=3, mapped_count=3, unmapped_count=0,
        mapping_status="complete",
        items=[
            NmckMappingItem(line_item_index=0, line_item_name="АВВГ", nmck_index=0,
                            nmck_name="АВВГ", nmck_price=None, match_score=1.0, match_method="fuzzy"),
        ],
    )
    missing = detect_missing_supplier_data(result)
    fields = [m.field for m in missing]
    assert "supplier_unit_price" in fields


# =============================================================================
# extract_required_documents tests
# =============================================================================


def test_extract_documents_from_cert_requirements():
    result = _make_result(
        certification_requirements=[
            HermesCertificationRequirement(requirement="Сертификат пожарной безопасности",
                                            source_document="tz.pdf", source_quote="требуется ССПБ",
                                            confidence=0.8),
        ],
    )
    docs = extract_required_documents(result)
    names = [d.name for d in docs]
    assert any("пожарной" in n for n in names)


def test_extract_documents_from_standards():
    result = _make_result()
    docs = extract_required_documents(result)
    names = [d.name for d in docs]
    assert any("ГОСТ 31996-2012" in n for n in names)


# =============================================================================
# build_questions_to_customer tests
# =============================================================================


def test_questions_include_delivery_if_missing():
    result = _make_result()
    result.summary.delivery_term = ""
    questions = build_questions_to_customer(result)
    texts = [q.question for q in questions]
    assert any("срок" in t.lower() for t in texts)


def test_questions_no_nmck():
    result = _make_result()
    result.nmck_mapping = NmckMappingResult(mapping_status="no_nmck_data")
    questions = build_questions_to_customer(result)
    texts = [q.question for q in questions]
    assert any("НМЦК" in t for t in texts)


# =============================================================================
# build_supplier_readiness_memo integration
# =============================================================================


def test_build_full_memo():
    result = _make_result()
    memo = build_supplier_readiness_memo(result)
    assert isinstance(memo, SupplierReadinessMemo)
    assert memo.tender_id == "test-tender"
    assert memo.supplier_readiness_score > 0


def test_memo_includes_rfq_requirements():
    result = _make_result()
    memo = build_supplier_readiness_memo(result)
    assert len(memo.rfq_requirements) == 3


def test_memo_includes_missing_supplier_data():
    result = _make_result()
    memo = build_supplier_readiness_memo(result)
    assert len(memo.missing_supplier_data) > 0


def test_memo_includes_next_actions():
    result = _make_result()
    memo = build_supplier_readiness_memo(result)
    assert len(memo.next_actions) > 0


# =============================================================================
# HermesRuntimeAnalysisResult with supplier_readiness_memo
# =============================================================================


def test_result_with_memo():
    result = _make_result()
    memo = build_supplier_readiness_memo(result)
    result.supplier_readiness_memo = memo
    assert result.supplier_readiness_memo is not None
    assert result.supplier_readiness_memo.bid_decision in ("go", "no_go", "needs_review")
