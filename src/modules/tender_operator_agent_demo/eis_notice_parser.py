from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from typing import Any


def extract_notice_metadata(xml_text: str) -> dict[str, Any]:
    if not xml_text or not xml_text.strip():
        return {}

    result: dict[str, Any] = {}
    source_label = "электронное извещение ЕИС"

    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return {}

    ns_map = _collect_namespaces(xml_text)

    result["nmck"] = _extract_value(
        root, ns_map,
        ("maxPrice", "initialPrice", "contractPrice", "initial_price", "price"),
        transform=_parse_price,
    )

    result["publication_date"] = _extract_value(
        root, ns_map,
        ("publishDate", "placingDate", "publicationDate", "publication_date", "createDate"),
        transform=_normalize_date,
    )

    result["submission_deadline"] = _extract_value(
        root, ns_map,
        ("endDate", "applicationEndDate", "collectingEndDate", "submissionDeadline", "deadline"),
        transform=_normalize_date,
    )

    result["delivery_term"] = _extract_value(
        root, ns_map,
        ("deliveryTerm", "deliveryTermInfo", "deliveryPeriod", "deliveryDate"),
    )

    result["customer_name"] = _extract_value(
        root, ns_map,
        ("placer", "customer", "customerInfo", "fullName", "legalEntityName"),
    )

    result["customer_inn"] = _extract_value(
        root, ns_map,
        ("inn", "customerInn", "placerInn"),
    )

    result["procurement_subject"] = _extract_value(
        root, ns_map,
        ("subject", "lotSubject", "procurementSubject", "contractSubject", "lotObjectInfo"),
    )

    procedure_type = _extract_value(
        root, ns_map,
        ("procedureType", "placingWayName", "purchaseMethod", "procedureTypeName"),
    )
    if procedure_type:
        result["procedure_type"] = procedure_type

    result["source_label"] = source_label

    if result.get("nmck") or result.get("publication_date") or result.get("submission_deadline"):
        result["_has_notice_data"] = True

    return result


def merge_structured_metadata(
    notice_meta: dict[str, Any],
    card_meta: dict[str, Any],
    doc_meta: dict[str, Any],
) -> dict[str, Any]:
    priority_sources = [
        ("eis_notice", notice_meta),
        ("card", card_meta),
        ("documents", doc_meta),
    ]

    result: dict[str, Any] = {}

    fields = [
        ("nmck", "initial_price"),
        ("publication_date", "publication_date"),
        ("submission_deadline", "deadline"),
        ("delivery_term", "delivery_term"),
        ("customer_name", "customer_name"),
        ("customer_inn", "customer_inn"),
        ("procurement_subject", "procurement_subject"),
        ("procedure_type", "procedure_type"),
    ]

    source_labels = {
        "eis_notice": "электронное извещение ЕИС",
        "card": "карточка ЕИС",
        "documents": "документы закупки",
    }

    for notice_key, output_key in fields:
        for source_name, meta in priority_sources:
            value = meta.get(notice_key)
            if value is not None:
                result[output_key] = {
                    "value": value,
                    "source": source_name,
                    "source_label": source_labels.get(source_name, source_name),
                }
                break

    return result


def apply_structured_metadata_to_procurement(
    procurement_payload: dict[str, Any],
    structured: dict[str, Any],
) -> None:
    source_labels = set()
    for key, entry in structured.items():
        if isinstance(entry, dict) and "value" in entry:
            source_labels.add(entry.get("source_label", ""))

    if structured.get("initial_price") and isinstance(structured["initial_price"], dict):
        procurement_payload["initial_price"] = structured["initial_price"]["value"]
    if structured.get("publication_date") and isinstance(structured["publication_date"], dict):
        procurement_payload["publication_date"] = structured["publication_date"]["value"]
    if structured.get("deadline") and isinstance(structured["deadline"], dict):
        procurement_payload["deadline"] = structured["deadline"]["value"]
    if structured.get("delivery_term") and isinstance(structured["delivery_term"], dict):
        procurement_payload["delivery_term"] = structured["delivery_term"]["value"]
    if structured.get("procedure_type") and isinstance(structured["procedure_type"], dict):
        procurement_payload["procedure_type"] = structured["procedure_type"]["value"]

    if source_labels:
        procurement_payload["structured_source_label"] = ", ".join(sorted(source_labels))

    if structured.get("nmck") and isinstance(structured["nmck"], dict):
        ns = structured["nmck"]
        if ns.get("source") == "eis_notice":
            procurement_payload["initial_price_source_priority"] = "eis_notice"
    if structured.get("publication_date") and isinstance(structured["publication_date"], dict):
        ns = structured["publication_date"]
        if ns.get("source") == "eis_notice":
            procurement_payload["publication_date_source_priority"] = "eis_notice"
    if structured.get("deadline") and isinstance(structured["deadline"], dict):
        ns = structured["deadline"]
        if ns.get("source") == "eis_notice":
            procurement_payload["deadline_source_priority"] = "eis_notice"


def build_notice_priority_prompt_section(procurement: dict[str, Any]) -> str:
    source_label = procurement.get("structured_source_label", "электронное извещение ЕИС")
    lines = ["Приоритетные сведения из электронного извещения ЕИС:"]
    nmck = procurement.get("initial_price")
    if nmck:
        lines.append(f"- НМЦК: {nmck} ₽")
    pub_date = procurement.get("publication_date")
    if pub_date:
        lines.append(f"- Дата публикации: {pub_date}")
    deadline = procurement.get("deadline")
    if deadline:
        lines.append(f"- Окончание подачи заявок: {deadline}")
    delivery = procurement.get("delivery_term")
    if delivery:
        lines.append(f"- Срок поставки: {delivery}")
    lines.append(f"- Источник: {source_label}")
    lines.append("")
    lines.append("Instruction: используй электронное извещение ЕИС как приоритетный источник структурных сведений. При расхождении с приложенными документами явно отметь расхождение и опирайся на извещение.")
    return "\n".join(lines)


def _collect_namespaces(xml_text: str) -> dict[str, str]:
    ns_map: dict[str, str] = {}
    for match in re.finditer(r'xmlns:?(\w*)\s*=\s*"([^"]+)"', xml_text):
        prefix = match.group(1) or "default"
        uri = match.group(2)
        ns_map[prefix] = uri
    return ns_map


def _extract_value(
    root: ET.Element,
    ns_map: dict[str, str],
    tag_names: tuple[str, ...],
    transform=None,
) -> Any:
    for tag in tag_names:
        for ns_prefix, ns_uri in ns_map.items():
            if ns_prefix == "default":
                full_tag = f"{{{ns_uri}}}{tag}"
            else:
                full_tag = f"{{{ns_uri}}}{tag}"
            found = root.find(f".//{full_tag}")
            if found is not None and found.text:
                val = found.text.strip()
                if transform:
                    val = transform(val)
                if val:
                    return val
        found = root.find(f".//{tag}")
        if found is not None and found.text:
            val = found.text.strip()
            if transform:
                val = transform(val)
            if val:
                return val
    return None


def _parse_price(value: str) -> float | None:
    try:
        cleaned = value.replace("\xa0", "").replace(" ", "").replace(",", ".")
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _normalize_date(value: str) -> str | None:
    if not value:
        return None
    match = re.match(r"(\d{4})-(\d{2})-(\d{2})", value)
    if match:
        return f"{match[3]}.{match[2]}.{match[1]}"
    match = re.match(r"(\d{2})\.(\d{2})\.(\d{4})", value)
    if match:
        return value
    return value
