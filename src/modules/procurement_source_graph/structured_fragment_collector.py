"""Convert existing extractor results into direct production fragments."""
from __future__ import annotations

from hashlib import sha256
import re
from .model import StructuredSourceFragment


def _normalize_characteristic_context(value: str) -> str:
    """Remove a repeated terminal condition while retaining the source raw text."""
    normalized = re.sub(r"\s+", " ", value).strip()
    voltage = re.compile(r"(?P<prefix>.*?)(?:напряжением\s+)(?P<condition>\d+(?:[.,]\d+)?\s*(?:В|V|вольт))\s+при\s+(?:напряжении\s+)?(?P=condition)\b", re.IGNORECASE)
    if voltage.search(normalized):
        return voltage.sub(r"\g<prefix>при напряжении \g<condition>", normalized)
    repeated = re.compile(r"(?P<condition>\d+(?:[.,]\d+)?\s*(?:°C|В|V|вольт|мл|г))\s+при\s+(?P=condition)\b", re.IGNORECASE)
    while repeated.search(normalized):
        normalized = repeated.sub(r"\g<condition>", normalized)
    # The collector may append the parsed numeric context to a name that
    # already contains the same condition.  Compare punctuation-insensitively:
    # "на 100 г. продукта, кКал при 100 г. продукта, кКал" and
    # "объёмом 2 мл, диаметром при 2 мл, диаметром" are both one condition.
    # Greedily select the final "при": an earlier genuine condition may be
    # part of the left-hand name, while the terminal one is the duplicated
    # context appended by the extractor.
    suffix = re.match(r"(?P<left>.+)\s+при\s+(?P<right>[^;]+)$", normalized, re.IGNORECASE)
    if suffix:
        compact = lambda text: re.sub(r"[^\w]+", "", text.casefold())
        if compact(suffix.group("left")).endswith(compact(suffix.group("right"))):
            return suffix.group("left").rstrip(" ,;")
    return normalized


class StructuredFragmentCollector:
    def collect_supply_items(self, procurement_number: str | None, items: list[object]) -> list[StructuredSourceFragment]:
        fragments: list[StructuredSourceFragment] = []
        for index, item in enumerate(items, 1):
            name = str(getattr(item, "name", "") or "")
            document = str(getattr(item, "source_document", "") or "")
            strategy = str(getattr(item, "extraction_strategy", "") or getattr(item, "source_kind", "") or "structured")
            if strategy in {"", "unknown"}:
                strategy = "xlsx_table" if document.lower().endswith((".xlsx", ".xls")) else "document_table"
            row = str(getattr(item, "source_row_number", "") or index)
            key = f"{procurement_number or 'unknown'}:{sha256((document + strategy + row + name).encode()).hexdigest()[:20]}"
            role = "service" if getattr(item, "item_type", "goods") == "service" else "item"
            fragment = StructuredSourceFragment(
                fragment_key=key, document_instance_id=document or f"document-{index}", source_type=strategy,
                locator=f"{document}:row:{row}", row_role=role, name=name, quantity=getattr(item, "quantity", None),
                unit=getattr(item, "unit", None),
                okpd2=getattr(item, "okpd2", None) or (getattr(item, "ktru", None) if str(getattr(item, "ktru", "")).startswith("23.") else None),
                ktru=None if str(getattr(item, "ktru", "")).startswith("23.") else getattr(item, "ktru", None),
                position_number=str(getattr(item, "item_no", "") or row), raw_text=str(getattr(item, "raw_fragment", "") or name),
                characteristics=tuple(str(value) for value in (getattr(item, "characteristics", None) or []) if value),
                provenance_kind="direct_source",
            )
            fragments.append(fragment)
            for characteristic_index, characteristic in enumerate(fragment.characteristics, 1):
                parse_text = (characteristic.replace("м[2*]", "м²").replace("см[2*]", "см²")
                              .replace("м[3*]", "м³").replace("см[3*]", "см³")
                              .replace("[0*]C", "°C").replace("ПРОЦ", "%"))
                # Pick the terminal comparison/value/unit block. Earlier
                # numeric tokens belong to the characteristic context (e.g.
                # "напряжением 24 В ≥ 4.2 А").
                matches = list(re.finditer(r"(?P<operator>≥|<=|>=|≤|>|<)?\s*(?P<value>-?\d+(?:[.,]\d+)?)(?:\s*(?P<unit>[A-Za-zА-Яа-я%²³°]+))?", parse_text))
                match = matches[-1] if matches else None
                characteristic_name = parse_text[:match.start()].strip(" ;,") if match else characteristic
                if match and len(matches) > 1:
                    context = characteristic[matches[0].start():match.start()].strip(" ;,")
                    characteristic_name = f"{characteristic_name} при {context}" if context else characteristic_name
                characteristic_name = _normalize_characteristic_context(
                    re.sub(r",?\s*градусы?$", "", characteristic_name, flags=re.IGNORECASE).strip()
                )
                fragments.append(StructuredSourceFragment(
                    fragment_key=f"{key}:characteristic:{characteristic_index}", document_instance_id=fragment.document_instance_id,
                    source_type=fragment.source_type, locator=f"{fragment.locator}:characteristic:{characteristic_index}",
                    row_role="item_characteristic", name=characteristic_name, raw_text=characteristic,
                    parent_fragment_key=fragment.fragment_key, provenance_kind="direct_source",
                    characteristic_name=characteristic_name,
                    characteristic_value=((match.group("operator") or "") + match.group("value")) if match else None,
                    characteristic_unit=("градус" if re.search(r"градусы?", parse_text, re.IGNORECASE) else (match.group("unit") or "").strip()) if match else None,
                ))
        return fragments
