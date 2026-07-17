"""Convert existing extractor results into direct production fragments."""
from __future__ import annotations

from hashlib import sha256
import re
from .model import StructuredSourceFragment


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
                characteristic_name = re.sub(r",?\s*градусы?$", "", characteristic_name, flags=re.IGNORECASE).strip()
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
