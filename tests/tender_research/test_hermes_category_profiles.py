from __future__ import annotations

from src.modules.hermes_agent.category import (
    _load_all_profiles,
    detect_procurement_category,
    list_available_categories,
    load_category_profile,
)
from src.modules.hermes_agent.schemas import (
    HermesAnalysisResponse,
    HermesLineItem,
    NormalizedLineItem,
)
from src.modules.hermes_agent.normalization import normalize_line_item, normalize_line_items


def test_load_all_profiles_returns_dict():
    profiles = _load_all_profiles()
    assert isinstance(profiles, dict)
    assert "general_goods" in profiles
    assert "electrical_goods" in profiles


def test_load_category_profile_electrical():
    profile = load_category_profile("electrical_goods")
    assert profile is not None
    assert profile["category"] == "electrical_goods"
    assert profile["label"] == "Электротехническая продукция"
    assert "signals" in profile
    assert "кабель" in profile["signals"]
    assert "required_fields" in profile
    assert "normalization_rules" in profile
    assert "quality_gates" in profile
    assert len(profile["quality_gates"]) == 5


def test_load_category_profile_general():
    profile = load_category_profile("general_goods")
    assert profile is not None
    assert profile["category"] == "general_goods"
    assert profile["label"] == "Общие товары"


def test_load_category_profile_unknown():
    profile = load_category_profile("nonexistent_category")
    assert profile is None


def test_list_available_categories():
    cats = list_available_categories()
    cat_keys = {c["category"] for c in cats}
    assert "general_goods" in cat_keys
    assert "electrical_goods" in cat_keys


def test_detect_procurement_category_electrical_by_signals():
    context = {
        "tender": {"title": "Поставка кабеля силового"},
        "documents": [
            {"file_name": "spec.pdf", "role": "specification", "text": "кабель АВВГ-П 2х2.5, провод СИП-4"},
        ],
    }
    cat = detect_procurement_category(context)
    assert cat == "electrical_goods"


def test_detect_procurement_category_electrical_by_title():
    context = {
        "tender": {"title": "Поставка кабельно-проводниковой продукции"},
        "documents": [],
    }
    cat = detect_procurement_category(context)
    assert cat == "electrical_goods"


def test_detect_procurement_category_general_when_no_signals():
    context = {
        "tender": {"title": "Поставка офисной мебели"},
        "documents": [],
    }
    cat = detect_procurement_category(context)
    assert cat == "general_goods"


def test_detect_procurement_category_with_line_item_names():
    context = {
        "tender": {"title": "Поставка продукции"},
        "documents": [],
    }
    cat = detect_procurement_category(context, line_item_names=["Кабель ВВГ 3х2.5", "Провод ПВС 3х1.5"])
    assert cat == "electrical_goods"


def test_detect_procurement_category_empty_returns_general():
    context = {"tender": {"title": ""}, "documents": []}
    cat = detect_procurement_category(context)
    assert cat == "general_goods"


# =============================================================================
# Normalization tests
# =============================================================================


def _make_item(name: str, **kwargs) -> HermesLineItem:
    return HermesLineItem(name=name, **kwargs)


def test_normalize_electrical_type_mark():
    profile = load_category_profile("electrical_goods")
    item = _make_item("Кабель АВВГ-П 2х2.5")
    norm = normalize_line_item(item, profile)
    assert norm.type_mark == "АВВГ"
    assert norm.normalized_name == "АВВГ / 2x2.5"
    assert norm.raw_name == "Кабель АВВГ-П 2х2.5"


def test_normalize_electrical_cores_and_section():
    profile = load_category_profile("electrical_goods")
    item = _make_item("Провод СИП-4 2х16, 0.6 кВ")
    norm = normalize_line_item(item, profile)
    assert norm.type_mark == "СИП"
    assert norm.cores_count == 2
    assert norm.cross_section_mm2 == 16.0
    assert norm.voltage == 0.6


def test_normalize_electrical_voltage():
    profile = load_category_profile("electrical_goods")
    item = _make_item("Кабель ВВГ-П 3х1.5, 1 кВ")
    norm = normalize_line_item(item, profile)
    assert norm.type_mark == "ВВГ"
    assert norm.voltage == 1.0


def test_normalize_electrical_standard():
    profile = load_category_profile("electrical_goods")
    item = _make_item("Кабель ВВГ-П 3х1.5", standards=["ГОСТ 31996-2012"])
    norm = normalize_line_item(item, profile)
    assert norm.standard == "ГОСТ 31996-2012"


def test_normalize_electrical_conductor_material():
    profile = load_category_profile("electrical_goods")
    # АВВГ starts with А -> aluminum
    item_al = _make_item("Кабель АВВГ 4х2.5")
    norm_al = normalize_line_item(item_al, profile)
    assert norm_al.conductor_material == "алюминий"

    # ВВГ starts with В -> copper
    item_cu = _make_item("Кабель ВВГ 3х1.5")
    norm_cu = normalize_line_item(item_cu, profile)
    assert norm_cu.conductor_material == "медь"


def test_normalize_electrical_equivalent_not_allowed():
    profile = load_category_profile("electrical_goods")
    item = _make_item("Кабель ВВГ-П 3х2.5, не допускается аналог")
    norm = normalize_line_item(item, profile)
    assert norm.equivalent_allowed is False


def test_normalize_no_profile_general():
    item = _make_item("Some item")
    norm = normalize_line_item(item, None)
    assert norm.normalized_name == "Some item"
    assert norm.type_mark is None


def test_normalize_line_items_batch():
    profile = load_category_profile("electrical_goods")
    items = [
        _make_item("Кабель АВВГ-П 2х2.5"),
        _make_item("Провод СИП-4 4х16, 1 кВ"),
    ]
    norms = normalize_line_items(items, profile)
    assert len(norms) == 2
    assert norms[0].type_mark == "АВВГ"
    assert norms[1].type_mark == "СИП"


# =============================================================================
# Category quality gates tests
# =============================================================================


def test_category_quality_gates_electrical():
    from src.modules.hermes_agent.quality import run_category_quality_gates

    profile = load_category_profile("electrical_goods")
    item = _make_item("Кабель ВВГ-П 3х1.5", quantity="100", unit="м")
    analysis = HermesAnalysisResponse(
        tender_id="test",
        summary={"subject": "Кабель"},
        line_items=[item],
    )
    norm = normalize_line_item(item, profile)

    checks = run_category_quality_gates(
        analysis, "electrical_goods",
        normalized_items=[norm],
    )
    check_names = [c.check_name for c in checks]
    assert "electrical_required_fields_present" in check_names
    assert "electrical_quantity_unit_required" in check_names
    assert "electrical_cable_type_mark_required" in check_names
    assert "electrical_standard_recommended" in check_names
    assert "electrical_nmck_mapping_complete" in check_names


def test_category_quality_gates_non_electrical():
    from src.modules.hermes_agent.quality import run_category_quality_gates

    analysis = HermesAnalysisResponse(tender_id="test")
    checks = run_category_quality_gates(analysis, "general_goods")
    assert checks == []


def test_electrical_type_mark_fails_for_cable_without_mark():
    from src.modules.hermes_agent.quality import run_category_quality_gates

    analysis = HermesAnalysisResponse(
        tender_id="test",
        line_items=[_make_item("Кабель без марки", quantity="100", unit="м")],
    )
    norm = NormalizedLineItem(raw_name="Кабель без марки", normalized_name="Кабель без марки")
    checks = run_category_quality_gates(
        analysis, "electrical_goods",
        normalized_items=[norm],
    )
    type_mark_check = [c for c in checks if c.check_name == "electrical_cable_type_mark_required"]
    assert len(type_mark_check) == 1
    assert type_mark_check[0].status == "failed"


def test_electrical_quantity_unit_fails():
    from src.modules.hermes_agent.quality import run_category_quality_gates

    analysis = HermesAnalysisResponse(
        tender_id="test",
        line_items=[_make_item("Кабель ВВГ 3х1.5", quantity="", unit="")],
    )
    checks = run_category_quality_gates(
        analysis, "electrical_goods",
        normalized_items=[NormalizedLineItem(raw_name="Кабель ВВГ 3х1.5", normalized_name="ВВГ")],
    )
    qty_check = [c for c in checks if c.check_name == "electrical_quantity_unit_required"]
    assert len(qty_check) == 1
    assert qty_check[0].status == "failed"
