from __future__ import annotations

import re
from typing import Any

from src.modules.hermes_agent.schemas import HermesLineItem, NormalizedLineItem


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _parse_via_patterns(text: str, patterns: list[str], extract_group: int = 1) -> str | None:
    text_lower = text.lower()
    for pat in patterns:
        m = re.search(pat, text_lower)
        if m:
            return m.group(extract_group).strip()
    return None


def _check_equivalent_allowed(text: str, patterns: list[str]) -> bool | None:
    text_lower = text.lower()
    has_analog = any(re.search(p, text_lower) for p in patterns)
    if has_analog:
        if "не допускается" in text_lower or "не доп" in text_lower:
            return False
        return True
    return None


def _infer_conductor_material(type_mark: str | None) -> str | None:
    if not type_mark:
        return None
    tm = type_mark.upper()
    if tm.startswith("А"):
        return "алюминий"
    if any(tm.startswith(p) for p in ("ВВГ", "КГ", "ПВС", "ШВВП", "КВВГ", "NYM", "NY")):
        return "медь"
    return None


def _infer_insulation_material(type_mark: str | None) -> str | None:
    if not type_mark:
        return None
    tm = type_mark.upper()
    if "НГ" in tm:
        return "ПВХ (пониженная горючесть)"
    if "LS" in tm or "LSL" in tm or "LOH" in tm:
        return "безгалогенная"
    if any(p in tm for p in ("ВВГ", "АВВГ", "КВВГ", "ПВС", "ШВВП")):
        return "ПВХ"
    if "NYM" in tm:
        return "ПВХ"
    return None


def normalize_line_item(
    item: HermesLineItem,
    profile: dict[str, Any] | None,
) -> NormalizedLineItem:
    name = _normalize_text(item.name)
    raw_name = name

    if profile is None or profile.get("category") != "electrical_goods":
        return NormalizedLineItem(
            raw_name=raw_name,
            normalized_name=name,
        )

    rules = profile.get("normalization_rules", {})

    type_mark = _parse_via_patterns(
        name,
        rules.get("type_mark", {}).get("patterns", []),
        extract_group=rules.get("type_mark", {}).get("extract_group", 1),
    )

    cores_count_str = _parse_via_patterns(
        name,
        rules.get("cores_count", {}).get("patterns", []),
        extract_group=rules.get("cores_count", {}).get("extract_group", 1),
    )

    cross_section_str = _parse_via_patterns(
        name,
        rules.get("cross_section_mm2", {}).get("patterns", []),
        extract_group=rules.get("cross_section_mm2", {}).get("extract_group", 1),
    )

    voltage_str = _parse_via_patterns(
        name,
        rules.get("voltage", {}).get("patterns", []),
        extract_group=rules.get("voltage", {}).get("extract_group", 1),
    )

    standard = _parse_via_patterns(
        f"{name} {' '.join(item.standards)}",
        rules.get("standard", {}).get("patterns", []),
        extract_group=rules.get("standard", {}).get("extract_group", 1),
    )

    equivalent_allowed = _check_equivalent_allowed(
        name,
        rules.get("equivalent_allowed", {}).get("patterns", []),
    )

    conductor_material = _infer_conductor_material(type_mark)
    insulation_material = _infer_insulation_material(type_mark)

    cores_count = int(cores_count_str) if cores_count_str and cores_count_str.isdigit() else None
    cross_section_mm2 = float(cross_section_str) if cross_section_str else None
    voltage = float(voltage_str) if voltage_str else None

    normalized_name_parts = []
    if type_mark:
        normalized_name_parts.append(type_mark.upper())
    if cores_count is not None and cross_section_mm2 is not None:
        normalized_name_parts.append(f"{cores_count}x{cross_section_mm2}")
    elif cross_section_mm2 is not None:
        normalized_name_parts.append(f"{cross_section_mm2} мм²")
    if voltage is not None:
        normalized_name_parts.append(f"{voltage} кВ")
    if standard:
        normalized_name_parts.append(standard.upper())

    if normalized_name_parts:
        normalized_name = " / ".join(normalized_name_parts)
    else:
        normalized_name = name

    return NormalizedLineItem(
        raw_name=raw_name,
        normalized_name=normalized_name,
        type_mark=type_mark.upper() if type_mark else None,
        cores_count=cores_count,
        cross_section_mm2=cross_section_mm2,
        voltage=voltage,
        conductor_material=conductor_material,
        insulation_material=insulation_material,
        standard=standard.upper() if standard else None,
        equivalent_allowed=equivalent_allowed,
    )


def normalize_line_items(
    items: list[HermesLineItem],
    profile: dict[str, Any] | None,
) -> list[NormalizedLineItem]:
    return [normalize_line_item(item, profile) for item in items]
