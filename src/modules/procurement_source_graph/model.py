"""Typed, fail-closed lineage primitives shared by report and audit builders."""
from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
import json
import re



ITEM_ROLES = frozenset({"item", "service", "work"})
REJECTED_ROLES = frozenset({"item_characteristic", "header", "field_label", "price_reference", "legal_instruction", "note", "requirement", "total", "empty", "unknown"})


def _tokens(value: str | None) -> set[str]:
    return {token for token in re.sub(r"[^a-zа-я0-9]+", " ", value or "", flags=re.IGNORECASE).lower().split() if len(token) >= 4}


@dataclass(frozen=True)
class StructuredSourceFragment:
    fragment_key: str
    document_instance_id: str
    source_type: str
    locator: str
    row_role: str
    name: str
    quantity: str | None = None
    unit: str | None = None
    okpd2: str | None = None
    ktru: str | None = None
    position_number: str | None = None
    raw_text: str = ""
    parent_fragment_key: str | None = None
    characteristics: tuple[str, ...] = ()
    characteristic_name: str | None = None
    characteristic_value: str | None = None
    characteristic_unit: str | None = None
    provenance_kind: str = "direct_source"


@dataclass(frozen=True)
class ValidatedPrimarySource:
    fragment: StructuredSourceFragment
    compatibility_evidence: tuple[str, ...]


@dataclass
class CanonicalProcurementItem:
    canonical_item_id: str
    official_name: str
    quantity: str | None
    unit: str | None
    primary_source: ValidatedPrimarySource | None
    warnings: list[str] = field(default_factory=list)
    field_provenance: dict[str, ValidatedPrimarySource] = field(default_factory=dict)
    characteristics: list[str] = field(default_factory=list)
    confirming_sources: list[ValidatedPrimarySource] = field(default_factory=list)
    complementary_sources: list[ValidatedPrimarySource] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    field_issues: list[dict[str, str]] = field(default_factory=list)
    display_name: str | None = None

    @property
    def status(self) -> str:
        if not self.primary_source or any(issue["severity"].startswith("blocking") for issue in self.field_issues):
            return "unresolved"
        return "confirmed_with_warnings" if self.field_issues or self.warnings else "confirmed"


@dataclass
class ProcurementSourceGraph:
    fragments: list[StructuredSourceFragment]
    canonical_items: list[CanonicalProcurementItem] = field(default_factory=list)

    def validate_primary(self, item_name: str, fragment: StructuredSourceFragment) -> ValidatedPrimarySource | None:
        if fragment is None:
            return None
        if fragment.row_role not in ITEM_ROLES or fragment.parent_fragment_key:
            return None
        overlap = _tokens(item_name) & _tokens(fragment.name)
        # A distinctive product token can bridge concise XML and fuller table
        # wording; generic labels remain insufficient proof of identity.
        generic = {"набор", "модуль", "электрод", "система", "изделие", "товар"}
        if len(overlap) < 2 and (len(overlap) != 1 or overlap <= generic):
            return None
        return ValidatedPrimarySource(fragment=fragment, compatibility_evidence=tuple(sorted(overlap)))

    def model_hash(self) -> str:
        payload = [
            {
                "id": item.canonical_item_id,
                "name": item.official_name,
                "quantity": item.quantity,
                "unit": item.unit,
                "characteristics": item.characteristics,
                "fields": {name: source.fragment.fragment_key for name, source in item.field_provenance.items()},
                "confirming": [source.fragment.fragment_key for source in item.confirming_sources],
                "complementary": [source.fragment.fragment_key for source in item.complementary_sources],
                "conflicts": item.conflicts,
                "warnings": item.warnings,
                "field_issues": item.field_issues,
            }
            for item in self.canonical_items
        ]
        return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


@dataclass
class CanonicalProcurementModel:
    procurement_number: str | None
    procurement_scope: str | None
    canonical_items: list[CanonicalProcurementItem]
    unresolved_candidates: list[CanonicalProcurementItem]
    source_graph_summary: dict[str, int]
    quality_issues: list[str]
    production_model_hash: str


def legacy_rows_to_canonical_model(procurement_number: str | None, scope: str | None, rows: list[dict]) -> CanonicalProcurementModel:
    """Compatibility adapter: legacy extraction may feed graph, never report directly."""
    graph = ProcurementSourceGraph([])
    confirmed: list[CanonicalProcurementItem] = []
    unresolved: list[CanonicalProcurementItem] = []
    used: set[str] = set()
    for index, row in enumerate(rows, 1):
        name = str(row.get("official_name") or row.get("name") or row.get("original_name") or "")
        source = str(row.get("source_document") or row.get("Источник") or "")
        fragment = StructuredSourceFragment(
            fragment_key=f"legacy-adapter:{index}:{sha256((source + name).encode()).hexdigest()[:12]}",
            document_instance_id=source or "legacy-document",
            source_type=str(row.get("extraction_strategy") or "legacy_adapter"), locator=str(row.get("source_row_number") or index),
            row_role="service" if row.get("item_type") == "service" or scope == "services" else "item", name=name,
            quantity=row.get("quantity"), unit=row.get("unit") or row.get("unit_original"), okpd2=row.get("okpd2"), ktru=row.get("ktru"),
        )
        graph.fragments.append(fragment)
        primary = (
            ValidatedPrimarySource(fragment=fragment, compatibility_evidence=("service_row",))
            if fragment.row_role == "service" and name
            else graph.validate_primary(name, fragment)
        )
        item = CanonicalProcurementItem(f"canonical-{index}", name, fragment.quantity, fragment.unit, primary)
        if primary:
            item.field_provenance["name"] = primary
            if fragment.quantity is not None:
                item.field_provenance["quantity"] = primary
            if fragment.unit is not None:
                item.field_provenance["unit"] = primary
            if fragment.okpd2:
                item.field_provenance["okpd2"] = primary
            if fragment.ktru:
                item.field_provenance["ktru"] = primary
        if primary and primary.fragment.fragment_key not in used:
            used.add(primary.fragment.fragment_key); confirmed.append(item)
        else:
            item.warnings.append("primary_source_unresolved"); unresolved.append(item)
    graph.canonical_items = confirmed + unresolved
    return CanonicalProcurementModel(procurement_number, scope, confirmed, unresolved, {"fragments": len(graph.fragments), "confirmed": len(confirmed), "unresolved": len(unresolved)}, [warning for item in unresolved for warning in item.warnings], graph.model_hash())


def direct_fragments_to_canonical_model(
    procurement_number: str | None,
    scope: str | None,
    fragments: list[StructuredSourceFragment],
    candidate_hints: list[dict],
) -> CanonicalProcurementModel:
    """Build goods canonical values exclusively from direct extractor fragments.

    Legacy rows are intentionally accepted only to establish the candidate order
    and provisional identity.  Their values never enter a canonical goods item.
    """
    # Local import keeps the resolver's dependency on fragment types acyclic.
    from .field_source_resolver import FieldSourceResolver

    graph = ProcurementSourceGraph(list(fragments))
    resolver = FieldSourceResolver()
    confirmed: list[CanonicalProcurementItem] = []
    unresolved: list[CanonicalProcurementItem] = []
    quality_issues: list[str] = []
    used_primary: set[str] = set()

    direct_hints: list[dict] = []
    for fragment in (fragment for fragment in fragments if fragment.row_role == "item"):
        # Reconcile only cross-document representations.  Same-document rows
        # are physical source positions and must remain independently visible.
        match = next((hint for hint in direct_hints if hint["_document"] != fragment.document_instance_id
                      and resolver.is_compatible(str(hint["name"]), fragment)
                      and (not hint.get("_quantity") or not fragment.quantity or hint["_quantity"] == fragment.quantity)
                      and (not hint.get("_unit") or not fragment.unit or hint["_unit"] == fragment.unit)), None)
        if match is None:
            direct_hints.append({"name": fragment.name, "stable_item_id": f"direct-{len(direct_hints) + 1}",
                                 "_document": fragment.document_instance_id, "_fragment_key": fragment.fragment_key,
                                 "_quantity": fragment.quantity, "_unit": fragment.unit})
    # Prefer native candidates whenever any direct item exists. Compatibility
    # hints are retained only for source absence, never for field values.
    active_hints = direct_hints or candidate_hints
    for index, hint in enumerate(active_hints, 1):
        hint_name = str(hint.get("official_name") or hint.get("name") or hint.get("original_name") or "")
        if not hint_name:
            continue
        resolved = resolver.resolve(hint_name, fragments, preferred_fragment_key=hint.get("_fragment_key"))
        name_field = resolved.fields.get("name")
        primary = graph.validate_primary(name_field.selected_value, next((f for f in fragments if f.fragment_key == name_field.source_fragment_key), None)) if name_field else None
        fields = resolved.fields
        item = CanonicalProcurementItem(
            canonical_item_id=str(hint.get("stable_item_id") or hint.get("canonical_item_id") or f"canonical-{index}"),
            official_name=name_field.selected_value if name_field else "",
            quantity=fields.get("quantity").selected_value if fields.get("quantity") else None,
            unit=fields.get("unit").selected_value if fields.get("unit") else None,
            primary_source=primary,
            characteristics=[],
            conflicts=list(resolved.conflicts),
        )
        if primary:
            seen_characteristics: set[tuple[str | None, str | None, str | None]] = set()
            for child in fragments:
                if child.row_role != "item_characteristic" or child.parent_fragment_key != primary.fragment.fragment_key:
                    continue
                if not child.characteristic_value:
                    item.warnings.append("CHARACTERISTIC_VALUE_ABSENT")
                    continue
                key = (child.characteristic_name, child.characteristic_value, child.characteristic_unit)
                if key in seen_characteristics:
                    continue
                seen_characteristics.add(key)
                raw_value = str(child.characteristic_value).strip()
                operator = "≥" if raw_value.startswith(("≥", ">=")) else "≤" if raw_value.startswith(("≤", "<=")) else ">" if raw_value.startswith(">") else "<" if raw_value.startswith("<") else None
                value = raw_value
                for prefix in ("≥", ">=", "≤", "<=", ">", "<"):
                    value = value.removeprefix(prefix)
                value = value.strip()
                item.characteristics.append({
                    "name": child.characteristic_name,
                    "operator": operator,
                    "value": value,
                    "unit": child.characteristic_unit,
                    "display_value": f"{child.characteristic_name}{(' ' + operator) if operator else ''} {value}{(' ' + child.characteristic_unit) if child.characteristic_unit else ''}",
                    "source_fragment_key": child.fragment_key,
                    "parent_fragment_key": child.parent_fragment_key,
                    "locator": child.locator,
                    "raw_value": child.raw_text,
                })
        for field_name, source in fields.items():
            if field_name == "characteristics":
                # Typed child rows below are the sole characteristic lineage.
                continue
            fragment = next((f for f in fragments if f.fragment_key == source.source_fragment_key), None)
            if not fragment or source.provenance_kind not in {"direct_source", "derived"}:
                raise AssertionError("CANONICAL_GOODS_VALUE_FROM_ADAPTER")
            validated = (
                ValidatedPrimarySource(fragment, ("direct_child_of_compatible_item",))
                if field_name == "characteristics" and fragment.parent_fragment_key
                else graph.validate_primary(item.official_name or hint_name, fragment)
            )
            if validated:
                item.field_provenance[field_name] = validated
        if primary:
            related = [f for f in fragments if f.fragment_key != primary.fragment.fragment_key and resolver.is_compatible(hint_name, f)]
            item.confirming_sources = [ValidatedPrimarySource(f, ("compatible_direct_source",)) for f in related]
            item.complementary_sources = [source for name, source in item.field_provenance.items() if name != "name" and source.fragment.fragment_key != primary.fragment.fragment_key]
        for field in resolved.unresolved_fields:
            issue = f"{field.upper()}_SOURCE_UNRESOLVED"
            item.warnings.append(issue)
            quality_issues.append(issue)
            severity = {
                "name": "blocking",
                "quantity": "blocking_for_commercial_analysis",
                "unit": "blocking_for_quantity_interpretation" if item.quantity is not None else "warning",
                "okpd2": "warning",
                "ktru": "warning",
            }.get(field, "warning")
            item.field_issues.append({"field_name": field, "severity": severity, "adjudication": "source_value_absent"})
        blocking = any(issue["severity"].startswith("blocking") for issue in item.field_issues)
        if not primary or primary.fragment.fragment_key in used_primary:
            if primary and primary.fragment.fragment_key in used_primary:
                item.warnings.append("PRIMARY_SOURCE_REUSED")
                quality_issues.append("PRIMARY_SOURCE_REUSED")
            unresolved.append(item)
        elif blocking:
            unresolved.append(item)
        else:
            used_primary.add(primary.fragment.fragment_key)
            confirmed.append(item)

    graph.canonical_items = confirmed + unresolved
    name_groups: dict[str, list[CanonicalProcurementItem]] = {}
    for item in graph.canonical_items:
        name_groups.setdefault(item.official_name, []).append(item)
    for group in name_groups.values():
        if len(group) < 2:
            continue
        for item in group:
            position = item.primary_source.fragment.position_number if item.primary_source else None
            if "distinguishing_values_missing" not in item.warnings:
                item.warnings.append("distinguishing_values_missing")
            # Preserve the official source wording; display is a separate view.
            item.display_name = f"{item.official_name} — позиция {position or item.canonical_item_id} извещения"
    return CanonicalProcurementModel(
        procurement_number, scope, graph.canonical_items, unresolved,
        {"fragments": len(fragments), "confirmed": len(confirmed), "unresolved": len(unresolved)},
        quality_issues, graph.model_hash(),
    )
