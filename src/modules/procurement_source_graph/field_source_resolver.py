"""Direct field-source resolution for production source fragments."""
from __future__ import annotations

from dataclasses import dataclass
import re

from .model import ITEM_ROLES, StructuredSourceFragment


@dataclass(frozen=True)
class FieldSource:
    field_name: str
    selected_value: str
    source_fragment_key: str
    provenance_kind: str
    source_type: str
    document_name: str
    locator: str
    raw_value: str
    normalized_value: str
    resolution_reason: str


@dataclass
class ResolvedFieldSources:
    fields: dict[str, FieldSource]
    unresolved_fields: list[str]
    conflicts: list[str]


def _tokens(value: str) -> set[str]:
    return {item for item in re.sub(r"[^a-zа-я0-9]+", " ", value.lower()).split() if len(item) >= 4}


GENERIC_TOKENS = frozenset({"набор", "модуль", "электрод", "контроллер", "питания", "система", "изделие", "товар"})
HARD_NEGATIVE_PAIRS = (
    ("грудной", "большеберц"),
    ("грудной", "плечев"),
    ("грудной", "лучев"),
    ("грудной", "локтев"),
    ("грудной", "лопаточ"),
    ("грудной", "лучезапяст"),
    ("грудной", "таз"),
    ("грудной", "кист"),
    ("большеберц", "плечев"),
    ("большеберц", "лучев"),
    ("большеберц", "локтев"),
    ("большеберц", "лопаточ"),
    ("большеберц", "лучезапяст"),
    ("большеберц", "таз"),
    ("большеберц", "кист"),
    ("плечев", "лучев"),
    ("плечев", "локтев"),
    ("плечев", "лопаточ"),
    ("плечев", "лучезапяст"),
    ("плечев", "таз"),
    ("плечев", "кист"),
    ("лучев", "локтев"),
    ("лучев", "лопаточ"),
    ("лучев", "лучезапяст"),
    ("лучев", "таз"),
    ("лучев", "кист"),
    ("локтев", "лопаточ"),
    ("локтев", "лучезапяст"),
    ("локтев", "таз"),
    ("локтев", "кист"),
    ("лопаточ", "лучезапяст"),
    ("лопаточ", "таз"),
    ("лопаточ", "кист"),
    ("лучезапяст", "таз"),
    ("лучезапяст", "кист"),
    ("таз", "кист"),
    ("ржан", "недлительн"),
    ("образец", "электрод"),
)


def _normalize_unit(value: str) -> str:
    normalized = value.strip().lower().replace(".", "")
    if normalized in {"усл ед", "услед", "условная единица"}:
        return "условная единица"
    return {"рул": "рулон", "шт": "штука"}.get(normalized, value.strip().lower())


class FieldSourceResolver:
    """Select direct structured fields; never substitutes an adapter source."""

    def is_compatible(self, official_name: str, fragment: StructuredSourceFragment) -> bool:
        if fragment.row_role not in ITEM_ROLES or fragment.parent_fragment_key:
            return False
        expected, actual = _tokens(official_name), _tokens(fragment.name)
        if any(
            any(token.startswith(left) for token in expected) and any(token.startswith(right) for token in actual)
            or any(token.startswith(right) for token in expected) and any(token.startswith(left) for token in actual)
            for left, right in HARD_NEGATIVE_PAIRS
        ):
            return False
        overlap = expected & actual
        if len(overlap) >= 2:
            return True
        # A distinctive direct token such as "Бикрост" can bridge a terse XML
        # name and a fuller XLSX/DOCX name. Generic labels may never do this.
        return len(overlap) == 1 and not overlap <= GENERIC_TOKENS

    def resolve(self, official_name: str, fragments: list[StructuredSourceFragment], *, preferred_fragment_key: str | None = None) -> ResolvedFieldSources:
        compatible = [f for f in fragments if self.is_compatible(official_name, f)]
        fields: dict[str, FieldSource] = {}
        unresolved: list[str] = []
        for field, attr in (("name", "name"), ("quantity", "quantity"), ("unit", "unit"), ("okpd2", "okpd2"), ("ktru", "ktru")):
            candidates = [f for f in compatible if getattr(f, attr)]
            # Price-calculation spreadsheets are the authoritative structured
            # source for quantity/unit/OKPD2 when they corroborate the notice.
            if field in {"quantity", "unit", "okpd2"}:
                candidates.sort(key=lambda f: ("xlsx" not in f.source_type.lower(), f.fragment_key != preferred_fragment_key, f.fragment_key))
            elif preferred_fragment_key:
                candidates.sort(key=lambda f: (f.fragment_key != preferred_fragment_key, f.fragment_key))
            source = candidates[0] if candidates else None
            if source is None:
                if field == "ktru":
                    continue
                unresolved.append(field)
                continue
            value = str(getattr(source, attr))
            normalized = _normalize_unit(value) if field == "unit" else value
            fields[field] = FieldSource(field, normalized, source.fragment_key, "direct_source", source.source_type, source.document_instance_id, source.locator, value, normalized, "direct compatible item fragment")
        compatible_keys = {fragment.fragment_key for fragment in compatible}
        characteristic_source = next((f for f in fragments if f.row_role == "item_characteristic" and f.parent_fragment_key in compatible_keys and f.characteristic_value), None)
        if characteristic_source:
            raw = characteristic_source.name
            fields["characteristics"] = FieldSource("characteristics", raw, characteristic_source.fragment_key, "direct_source", characteristic_source.source_type, characteristic_source.document_instance_id, characteristic_source.locator, raw, raw, "direct child characteristic")
        elif (item_source := next((f for f in compatible if f.characteristics), None)):
            raw = "; ".join(item_source.characteristics)
            fields["characteristics"] = FieldSource("characteristics", raw, item_source.fragment_key, "direct_source", item_source.source_type, item_source.document_instance_id, item_source.locator, raw, raw, "direct item characteristic")
        return ResolvedFieldSources(fields, unresolved, [])
