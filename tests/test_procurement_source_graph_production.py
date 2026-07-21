from __future__ import annotations

from src.modules.procurement_source_graph.field_source_resolver import FieldSourceResolver
from src.modules.procurement_source_graph.model import StructuredSourceFragment, direct_fragments_to_canonical_model
from src.modules.procurement_source_graph.serialization import provenance_records, serialize_graph
from src.modules.procurement_source_graph.structured_fragment_collector import _normalize_characteristic_context


def _fragment(key: str, name: str, *, quantity: str | None = "10", unit: str | None = "шт", source: str = "xlsx_table", document: str | None = None) -> StructuredSourceFragment:
    return StructuredSourceFragment(key, document or f"{key}.xlsx", source, f"{key}:1", "item", name, quantity=quantity, unit=unit)


def test_production_builder_uses_direct_resolver_values_not_candidate_values():
    fragment = _fragment("direct", "Бикрост", quantity="10", unit="рул")
    model = direct_fragments_to_canonical_model("n", "goods", [fragment], [{"name": "Бикрост", "quantity": "999", "unit": "кг"}])
    item = model.canonical_items[0]
    assert (item.official_name, item.quantity, item.unit) == ("Бикрост", "10", "рулон")
    assert all(source.fragment.provenance_kind == "direct_source" for source in item.field_provenance.values())


def test_direct_candidate_discovery_keeps_same_document_source_positions_separate():
    fragments = [_fragment("one", "Блок питания", quantity="5", document="source.xlsx"), _fragment("two", "Блок питания", quantity="10", document="source.xlsx")]
    model = direct_fragments_to_canonical_model("n", "goods", fragments, [])
    assert [item.quantity for item in model.canonical_items] == ["5", "10"]
    assert not any("PRIMARY_SOURCE_REUSED" in item.warnings for item in model.canonical_items)


def test_hard_negative_prevents_anatomically_different_endoprosthesis_match():
    resolver = FieldSourceResolver()
    chest = _fragment("chest", "Индивидуальный эндопротез грудной стенки")
    tibia = _fragment("tibia", "Индивидуальный эндопротез большеберцовой кости")
    assert resolver.is_compatible(chest.name, chest)
    assert not resolver.is_compatible(chest.name, tibia)


def test_one_to_one_xml_version_reconciliation_preserves_anatomical_identity():
    fragments = [
        _fragment("a-chest", "Индивидуальный эндопротез грудной стенки", document="a.xml"),
        _fragment("a-tibia", "Индивидуальный эндопротез большеберцовой кости", document="a.xml"),
        _fragment("b-chest", "Индивидуальный эндопротез грудной стенки", document="b.xml"),
        _fragment("b-tibia", "Индивидуальный эндопротез большеберцовой кости", document="b.xml"),
    ]
    model = direct_fragments_to_canonical_model("n", "goods", fragments, [])
    graph = serialize_graph(model, fragments, "test")
    assert {(edge["left_fragment_key"], edge["right_fragment_key"]) for edge in graph["cross_source_matches"]} == {
        ("a-chest", "b-chest"), ("a-tibia", "b-tibia")
    }
    assert {row["canonical_item_id"] for row in graph["cardinality_decisions"] if row["source_fragment_key"].startswith("b-")} == {"direct-1", "direct-2"}


def test_bread_types_and_duplicate_name_groups_do_not_create_cartesian_cross_edges():
    bread = [_fragment("a", "Хлеб недлительного хранения", document="a.xml"), _fragment("b", "Хлеб ржаной", document="b.xml")]
    assert serialize_graph(direct_fragments_to_canonical_model("n", "goods", bread, []), bread, "test")["cross_source_matches"] == []
    holders = [
        _fragment("a-1", "Держатель", document="a.xml"), _fragment("a-2", "Держатель", document="a.xml"),
        _fragment("b-1", "Держатель", document="b.xml"), _fragment("b-2", "Держатель", document="b.xml"),
    ]
    graph = serialize_graph(direct_fragments_to_canonical_model("n", "goods", holders, []), holders, "test")
    assert graph["cross_source_matches"] == []
    assert {row["decision"] for row in graph["cardinality_decisions"] if row["source_fragment_key"].startswith("b-")} == {"ambiguous_candidate"}


def test_provenance_schema_preserves_raw_main_values_and_normalizes_conditional_unit():
    fragment = _fragment("one", "Позиция", quantity="2", unit="усл. ед.")
    model = direct_fragments_to_canonical_model("n", "goods", [fragment], [])
    records = provenance_records(model)
    unit = next(record for record in records if record.field_name == "unit")
    assert unit.selected_value == "условная единица"
    assert unit.raw_value == "усл. ед."
    assert all(record.raw_value and record.source_fragment_key and record.locator and record.resolution_reason for record in records if record.field_name in {"name", "quantity", "unit"})


def test_generic_characteristic_context_deduplication():
    assert _normalize_characteristic_context("при температуре 23°C при 23°C") == "при температуре 23°C"
    assert _normalize_characteristic_context("на 100 г продукта при 100 г продукта") == "на 100 г продукта"
    assert _normalize_characteristic_context("шприц объёмом 2 мл при 2 мл") == "шприц объёмом 2 мл"
    assert _normalize_characteristic_context("влажность при 25°C без конденсации при 25°C без конденсации") == "влажность при 25°C без конденсации"
    assert _normalize_characteristic_context("напряжением 24 В при 24 В") == "при напряжении 24 В"
