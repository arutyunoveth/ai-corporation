from __future__ import annotations

import logging
import re
from difflib import SequenceMatcher
from typing import Any

from src.modules.hermes_agent.schemas import (
    HermesLineItem,
    NmckLine,
    NmckMappingItem,
    NmckMappingResult,
    NormalizedLineItem,
)

logger = logging.getLogger(__name__)


def extract_nmck_lines(documents: list[dict[str, Any]]) -> list[NmckLine]:
    lines: list[NmckLine] = []
    for doc in documents:
        role = (doc.get("role") or "").lower()
        if "nmck" not in role and "расчет" not in role and "нмцк" not in role:
            continue

        text = doc.get("text") or ""
        tables = doc.get("tables") or []

        table_lines = _extract_from_tables(tables)
        lines.extend(table_lines)

        text_lines = _extract_from_text(text, doc.get("file_name", ""))
        lines.extend(text_lines)

    return lines


def _extract_from_tables(tables: list[dict[str, Any]]) -> list[NmckLine]:
    lines: list[NmckLine] = []
    for table in tables:
        raw_lines = table.get("lines") or []
        text = table.get("text") or ""
        if not raw_lines and text:
            raw_lines = text.split("\n")
        for row in raw_lines:
            cells = [c.strip() for c in re.split(r"\||\t", row) if c.strip()]
            if len(cells) >= 2:
                name = cells[0]
                if _looks_like_line_item(name):
                    quantity = ""
                    unit = ""
                    price = ""
                    amount = ""
                    for cell in cells[1:]:
                        cell_clean = cell.replace(",", ".").strip()
                        if re.match(r"^\d+(?:\.\d+)?$", cell_clean):
                            if not quantity:
                                quantity = cell_clean
                            elif not price:
                                price = cell_clean
                            elif not amount:
                                amount = cell_clean
                    if not unit and len(cells) > 1:
                        unit_cell = cells[1] if len(cells) > 1 else ""
                        if re.match(r"^[^\d]+$", unit_cell.strip()):
                            unit = unit_cell.strip()
                    lines.append(NmckLine(
                        name=name,
                        quantity=quantity,
                        unit=unit,
                        price=price,
                        total_amount=amount,
                    ))
    return lines


def _extract_from_text(text: str, source: str) -> list[NmckLine]:
    lines: list[NmckLine] = []
    if not text:
        return lines

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue
        if not _looks_like_line_item(stripped):
            continue
        cells = [c.strip() for c in re.split(r"\s{2,}|\t", stripped) if c.strip()]
        if len(cells) < 2:
            continue
        name = cells[0]
        quantity = ""
        unit = ""
        price = ""
        amount = ""
        for cell in cells[1:]:
            cell_clean = cell.replace(",", ".").strip()
            if re.match(r"^\d+(?:\.\d+)?$", cell_clean):
                if not quantity:
                    quantity = cell_clean
                elif not price:
                    price = cell_clean
                elif not amount:
                    amount = cell_clean
        lines.append(NmckLine(
            name=name,
            quantity=quantity,
            unit=unit,
            price=price,
            total_amount=amount,
        ))
    return lines


def _looks_like_line_item(text: str) -> bool:
    if not text or len(text) < 3:
        return False
    text_lower = text.lower()
    skip_words = {"итого", "всего", "наименование", "№", "п/п", "номер", "сумма"}
    for sw in skip_words:
        if text_lower.strip() == sw or text_lower.startswith(sw):
            return False
    return True


def _fuzzy_score(a: str, b: str) -> float:
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def map_line_items_to_nmck(
    line_items: list[HermesLineItem],
    normalized_items: list[NormalizedLineItem],
    nmck_lines: list[NmckLine],
    profile: dict[str, Any] | None,
) -> NmckMappingResult:
    if not nmck_lines:
        return NmckMappingResult(
            total_nmck_lines=0,
            mapped_count=0,
            mapping_status="no_nmck_data",
            items=[],
        )

    settings = (profile or {}).get("nmck_mapping_settings", {})
    match_by = settings.get("match_by", ["normalized_name", "type_mark", "name"])
    threshold = settings.get("fuzzy_threshold", 0.7)

    mapped_items: list[NmckMappingItem] = []
    for i, item in enumerate(line_items):
        norm = normalized_items[i] if i < len(normalized_items) else None
        search_texts: list[str] = []
        for field in match_by:
            if norm and field == "normalized_name":
                search_texts.append(norm.normalized_name)
            elif norm and field == "type_mark" and norm.type_mark:
                search_texts.append(norm.type_mark)
            elif field == "name":
                search_texts.append(item.name)
        search_texts = [t for t in search_texts if t]

        best_match: NmckLine | None = None
        best_score = 0.0
        for nmck_line in nmck_lines:
            for search_text in search_texts:
                score = _fuzzy_score(search_text, nmck_line.name)
                if score > best_score:
                    best_score = score
                    best_match = nmck_line

        if best_match and best_score >= threshold:
            mapped_items.append(NmckMappingItem(
                line_item_index=i,
                line_item_name=item.name,
                nmck_index=nmck_lines.index(best_match),
                nmck_name=best_match.name,
                nmck_price=best_match.price,
                nmck_total_amount=best_match.total_amount,
                match_score=round(best_score, 3),
                match_method="fuzzy",
            ))
        else:
            mapped_items.append(NmckMappingItem(
                line_item_index=i,
                line_item_name=item.name,
                nmck_index=None,
                nmck_name=None,
                nmck_price=None,
                nmck_total_amount=None,
                match_score=round(best_score, 3) if best_match else 0.0,
                match_method="none",
            ))

    mapped_count = sum(1 for m in mapped_items if m.nmck_index is not None)
    mapping_status = "complete" if mapped_count == len(line_items) else "partial"

    return NmckMappingResult(
        total_nmck_lines=len(nmck_lines),
        mapped_count=mapped_count,
        unmapped_count=len(line_items) - mapped_count,
        mapping_status=mapping_status,
        items=mapped_items,
    )
