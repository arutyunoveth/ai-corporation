from __future__ import annotations

from src.modules.procurement_source_graph.field_source_resolver import FieldSourceResolver
from src.modules.procurement_source_graph.model import StructuredSourceFragment, direct_fragments_to_canonical_model


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
