from __future__ import annotations

from src.modules.hermes_agent.nmck_mapping import (
    _extract_from_tables,
    _extract_from_text,
    _fuzzy_score,
    _looks_like_line_item,
    extract_nmck_lines,
    map_line_items_to_nmck,
)
from src.modules.hermes_agent.schemas import (
    HermesLineItem,
    NmckLine,
    NmckMappingResult,
    NormalizedLineItem,
)


# =============================================================================
# NMCK extraction tests
# =============================================================================


def test_looks_like_line_item_valid():
    assert _looks_like_line_item("Кабель АВВГ-П 2х2.5") is True
    assert _looks_like_line_item("Провод СИП-4 2х16") is True


def test_looks_like_line_item_skip_headers():
    assert _looks_like_line_item("Итого") is False
    assert _looks_like_line_item("Всего") is False
    assert _looks_like_line_item("Наименование") is False


def test_looks_like_line_item_too_short():
    assert _looks_like_line_item("ab") is False
    assert _looks_like_line_item("") is False


def test_extract_from_tables_empty():
    result = _extract_from_tables([])
    assert result == []


def test_extract_from_tables_with_data():
    tables = [
        {
            "lines": [
                "Кабель АВВГ-П 2х2.5|м|200|50|10000",
                "Провод СИП-4 4х16|м|700|120|84000",
            ]
        }
    ]
    lines = _extract_from_tables(tables)
    assert len(lines) == 2
    assert lines[0].name == "Кабель АВВГ-П 2х2.5"
    assert lines[0].quantity == "200"
    assert lines[0].unit == "м"
    assert lines[1].name == "Провод СИП-4 4х16"


def test_extract_from_text_with_data():
    text = "Кабель АВВГ-П 2х2.5\tм\t200\t50\t10000\nПровод СИП-4 4х16\tм\t700\t120\t84000"
    lines = _extract_from_text(text, "nmck.pdf")
    assert len(lines) == 2
    assert lines[0].name == "Кабель АВВГ-П 2х2.5"
    assert lines[0].quantity == "200"


def test_extract_nmck_lines_skips_non_nmck():
    docs = [
        {"role": "specification", "text": "Some spec text"},
        {"role": "notice", "text": "Some notice"},
    ]
    lines = extract_nmck_lines(docs)
    assert lines == []


def test_extract_nmck_lines_from_nmck_doc():
    docs = [
        {"role": "nmck_calculation", "text": "Кабель ВВГ 3х1.5\tм\t500\t80\t40000", "tables": []},
    ]
    lines = extract_nmck_lines(docs)
    assert len(lines) == 1
    assert lines[0].name == "Кабель ВВГ 3х1.5"


# =============================================================================
# Fuzzy matching tests
# =============================================================================


def test_fuzzy_score_exact():
    score = _fuzzy_score("Кабель АВВГ-П 2х2.5", "Кабель АВВГ-П 2х2.5")
    assert score == 1.0


def test_fuzzy_score_similar():
    score = _fuzzy_score("Кабель АВВГ-П 2х2.5", "АВВГ-П 2х2.5")
    assert score > 0.5


def test_fuzzy_score_different():
    score = _fuzzy_score("Кабель АВВГ", "Стул офисный")
    assert score < 0.3


# =============================================================================
# NMCK mapping tests
# =============================================================================


def _make_line_item(name: str, **kwargs) -> HermesLineItem:
    return HermesLineItem(name=name, **kwargs)


def _make_normalized(name: str, type_mark: str | None = None, **kwargs) -> NormalizedLineItem:
    return NormalizedLineItem(raw_name=name, normalized_name=name, type_mark=type_mark, **kwargs)


def test_map_no_nmck_lines():
    items = [_make_line_item("Кабель АВВГ-П 2х2.5")]
    norms = [_make_normalized("Кабель АВВГ-П 2х2.5", "АВВГ")]
    result = map_line_items_to_nmck(items, norms, [], None)
    assert result.mapping_status == "no_nmck_data"
    assert result.total_nmck_lines == 0
    assert result.mapped_count == 0


def test_map_complete_match():
    items = [_make_line_item("Кабель АВВГ-П 2х2.5")]
    norms = [_make_normalized("Кабель АВВГ-П 2х2.5", "АВВГ")]
    nmck_lines = [NmckLine(name="Кабель АВВГ-П 2х2.5", quantity="200", unit="м", price="50", total_amount="10000")]
    result = map_line_items_to_nmck(items, norms, nmck_lines, None)
    assert result.mapping_status == "complete"
    assert result.mapped_count == 1
    assert result.total_nmck_lines == 1
    assert len(result.items) == 1
    assert result.items[0].nmck_name == "Кабель АВВГ-П 2х2.5"


def test_map_partial_match():
    items = [
        _make_line_item("Кабель АВВГ-П 2х2.5"),
        _make_line_item("Стул офисный"),
    ]
    norms = [
        _make_normalized("Кабель АВВГ-П 2х2.5", "АВВГ"),
        _make_normalized("Стул офисный"),
    ]
    nmck_lines = [NmckLine(name="Кабель АВВГ-П 2х2.5", quantity="200", unit="м", price="50", total_amount="10000")]
    result = map_line_items_to_nmck(items, norms, nmck_lines, None)
    assert result.mapping_status == "partial"
    assert result.mapped_count == 1
    assert result.unmapped_count == 1


def test_map_with_electrical_profile():
    from src.modules.hermes_agent.category import load_category_profile

    profile = load_category_profile("electrical_goods")
    items = [_make_line_item("Кабель АВВГ-П 2х2.5")]
    norms = [_make_normalized("Кабель АВВГ-П 2х2.5", "АВВГ")]
    nmck_lines = [NmckLine(name="АВВГ", quantity="200", unit="м", price="50", total_amount="10000")]
    result = map_line_items_to_nmck(items, norms, nmck_lines, profile)
    assert result.mapped_count == 1
    assert result.items[0].match_method == "fuzzy"


def test_map_unmatched_item_has_no_nmck_index():
    items = [_make_line_item("Something completely different")]
    norms = [_make_normalized("Something completely different")]
    nmck_lines = [NmckLine(name="Кабель АВВГ", quantity="100", unit="м", price="50")]
    result = map_line_items_to_nmck(items, norms, nmck_lines, None)
    assert result.items[0].nmck_index is None
    assert result.items[0].match_method == "none"


def test_nmck_mapping_result_model():
    result = NmckMappingResult(
        total_nmck_lines=5,
        mapped_count=3,
        unmapped_count=2,
        mapping_status="partial",
        items=[],
    )
    assert result.mapping_status == "partial"
    assert result.total_nmck_lines == 5
