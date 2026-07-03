from __future__ import annotations

import re
from dataclasses import dataclass

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.supplier_registry.models import SupplierContact, SupplierExternalRef, SupplierProfile, SupplierTag
from src.modules.supplier_search.models import SupplierShortlist, SupplierShortlistRow
from src.modules.supplier_search.schemas import BuildSupplierShortlistRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, SupplierShortlistStatus, SupplierStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_supplier_shortlist_id
from src.shared.supplier_package import load_analysis_package


DEFAULT_SHORTLIST_TOP_N = 5
SCORE_WEIGHTS = {
    "category_match": 30,
    "brand_match": 20,
    "region_match": 10,
    "email_exists": 10,
    "phone_exists": 5,
    "website_exists": 5,
    "source_vendor_list": 10,
    "tender_ready": 10,
    "requirement_signal_match": 10,
    "needs_review_penalty": -10,
}

_TAG_TRANSLITERATION = str.maketrans(
    {
        "а": "a",
        "б": "b",
        "в": "v",
        "г": "g",
        "д": "d",
        "е": "e",
        "ё": "e",
        "ж": "zh",
        "з": "z",
        "и": "i",
        "й": "y",
        "к": "k",
        "л": "l",
        "м": "m",
        "н": "n",
        "о": "o",
        "п": "p",
        "р": "r",
        "с": "s",
        "т": "t",
        "у": "u",
        "ф": "f",
        "х": "h",
        "ц": "ts",
        "ч": "ch",
        "ш": "sh",
        "щ": "sch",
        "ъ": "",
        "ы": "y",
        "ь": "",
        "э": "e",
        "ю": "yu",
        "я": "ya",
    }
)


@dataclass(slots=True)
class SupplierSearchContext:
    category_signals: set[str]
    brand_signals: set[str]
    region_signals: set[str]
    requirement_tokens: set[str]
    domain_signal: str


@dataclass(slots=True)
class RankedSupplier:
    supplier: SupplierProfile
    score: int
    inclusion_reason: str
    source_type: str


def _transliterate(text: str) -> str:
    lowered = text.lower()
    output: list[str] = []
    for char in lowered:
        mapped = _TAG_TRANSLITERATION.get(ord(char))
        if mapped is not None:
            output.append(mapped)
        else:
            output.append(char)
    return "".join(output)


def _canonical_signal(value: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", _transliterate(value)).strip("_").upper()
    normalized = re.sub(r"_+", "_", normalized)
    return normalized


def _tokenize_text(value: str) -> set[str]:
    translated = _transliterate(value.lower())
    return {token for token in re.findall(r"[a-z0-9]{3,}", translated)}


def _tag_set(session: Session, supplier_id: str) -> set[str]:
    return {
        str(tag)
        for tag in session.scalars(select(SupplierTag.tag_code).where(SupplierTag.supplier_id == supplier_id))
    }


def _contact_signals(session: Session, supplier_id: str) -> tuple[bool, bool]:
    contacts = list(session.scalars(select(SupplierContact).where(SupplierContact.supplier_id == supplier_id)))
    has_email = any(contact.email for contact in contacts)
    has_phone = any(contact.phone for contact in contacts)
    return has_email, has_phone


def _website_exists(session: Session, supplier_id: str) -> bool:
    refs = list(
        session.scalars(
            select(SupplierExternalRef).where(
                SupplierExternalRef.supplier_id == supplier_id,
                SupplierExternalRef.ref_type == "website",
            )
        )
    )
    return any(ref.ref_value for ref in refs)


def _domain_signal(package) -> str:
    return str(package.deal.domain_type or "").upper()


def _context_from_texts(*texts: str, domain_signal: str = "") -> SupplierSearchContext:
    category_signals: set[str] = set()
    brand_signals: set[str] = set()
    region_signals: set[str] = set()
    requirement_tokens: set[str] = set()

    if domain_signal:
        category_signals.add(domain_signal)
        category_signals.add(f"CATEGORY_{_canonical_signal(domain_signal)}")

    for text in texts:
        if not text:
            continue
        requirement_tokens.update(_tokenize_text(text))
        signal = _canonical_signal(text)
        if signal:
            category_signals.add(f"CATEGORY_{signal}")
            region_signals.add(f"REGION_{signal}")
        for token in _tokenize_text(text):
            category_signals.add(f"CATEGORY_{token.upper()}")
            brand_signals.add(f"BRAND_{token.upper()}")
            region_signals.add(f"REGION_{token.upper()}")

    return SupplierSearchContext(
        category_signals=category_signals,
        brand_signals=brand_signals,
        region_signals=region_signals,
        requirement_tokens=requirement_tokens,
        domain_signal=domain_signal,
    )


def _build_context_from_package(package) -> SupplierSearchContext:
    texts = [
        str(package.deal.title or ""),
        str(package.tender_summary.summary_text or ""),
        str(package.tender_summary.structured_summary_json.get("high_level_scope") or ""),
        str(package.tender_summary.structured_summary_json.get("title") or ""),
    ]
    if package.document_requirement_rows:
        for row in package.document_requirement_rows:
            texts.extend(
                [
                    str(row.requirement_title or ""),
                    str(row.requirement_description or ""),
                    str(row.requirement_category or ""),
                ]
            )
    return _context_from_texts(*texts, domain_signal=_domain_signal(package))


def build_context_from_requirements(requirements: dict[str, object]) -> SupplierSearchContext:
    texts: list[str] = [str(requirements.get("tender_summary") or "")]
    for field in ("technical_requirements", "qualification_requirements", "document_requirements", "evaluation_criteria", "procurement_categories"):
        for item in requirements.get(field, []) if isinstance(requirements.get(field), list) else []:
            texts.append(str(item))
    domain_signal = _canonical_signal(" ".join(str(item) for item in requirements.get("procurement_categories", [])[:1])) if isinstance(requirements.get("procurement_categories"), list) else ""
    return _context_from_texts(*texts, domain_signal=domain_signal)


def _source_type(tags: set[str]) -> str:
    if "SOURCE_VENDOR_LIST_ENRICHED" in tags:
        return "REGISTRY_VENDOR_LIST"
    if "SOURCE_VENDOR_LIST" in tags:
        return "VENDOR_LIST"
    return "REGISTRY"


def rank_suppliers_for_context(session: Session, context: SupplierSearchContext, *, top_n: int = DEFAULT_SHORTLIST_TOP_N) -> list[RankedSupplier]:
    candidates = list(
        session.scalars(
            select(SupplierProfile)
            .where(SupplierProfile.status.in_([SupplierStatus.ACTIVE, SupplierStatus.DRAFT]))
            .order_by(SupplierProfile.created_at.asc(), SupplierProfile.id.asc())
        )
    )
    ranked: list[RankedSupplier] = []
    for supplier in candidates:
        score = 0
        reasons: list[str] = []
        tags = _tag_set(session, supplier.supplier_id)
        source_type = _source_type(tags)
        combined_text = " ".join(
            [
                supplier.legal_name or "",
                supplier.display_name or "",
                supplier.notes or "",
                " ".join(tags),
            ]
        )
        supplier_tokens = _tokenize_text(combined_text)
        has_email, has_phone = _contact_signals(session, supplier.supplier_id)
        has_website = _website_exists(session, supplier.supplier_id)

        matched_category_tags = sorted(
            tag for tag in tags if tag in context.category_signals or (context.domain_signal and tag == context.domain_signal)
        )
        if matched_category_tags:
            score += SCORE_WEIGHTS["category_match"]
            reasons.append(f"category match {'/'.join(matched_category_tags[:3])}")

        matched_brand_tags = sorted(tag for tag in tags if tag in context.brand_signals)
        if matched_brand_tags:
            score += SCORE_WEIGHTS["brand_match"]
            reasons.append(f"brand match {'/'.join(matched_brand_tags[:3])}")

        matched_region_tags = sorted(tag for tag in tags if tag in context.region_signals)
        if matched_region_tags:
            score += SCORE_WEIGHTS["region_match"]
            reasons.append(f"region match {'/'.join(matched_region_tags[:3])}")

        if has_email:
            score += SCORE_WEIGHTS["email_exists"]
            reasons.append("email available")
        if has_phone:
            score += SCORE_WEIGHTS["phone_exists"]
            reasons.append("phone available")
        if has_website:
            score += SCORE_WEIGHTS["website_exists"]
            reasons.append("website available")
        if "SOURCE_VENDOR_LIST" in tags:
            score += SCORE_WEIGHTS["source_vendor_list"]
            reasons.append("source vendor-list")
        if "TENDER_READY" in tags:
            score += SCORE_WEIGHTS["tender_ready"]
            reasons.append("tender-ready tag")

        matched_tokens = sorted(context.requirement_tokens.intersection(supplier_tokens))
        if matched_tokens:
            score += SCORE_WEIGHTS["requirement_signal_match"]
            reasons.append(f"requirement/domain signal match {'/'.join(matched_tokens[:4])}")

        if supplier.status != SupplierStatus.ACTIVE or "NEEDS_REVIEW_NO_INN" in tags or "POSSIBLE_DUPLICATE_VENDOR_LIST" in tags:
            score += SCORE_WEIGHTS["needs_review_penalty"]
            reasons.append("needs review")

        if supplier.country_code == "RU":
            reasons.append("RU registry presence")

        inclusion_reason = f"score={score}; source={source_type}; " + "; ".join(reasons or ["Active supplier from reusable registry"])
        ranked.append(
            RankedSupplier(
                supplier=supplier,
                score=score,
                inclusion_reason=inclusion_reason,
                source_type=source_type,
            )
        )

    ranked.sort(key=lambda item: (-item.score, item.supplier.created_at, item.supplier.supplier_id))
    return ranked[: max(top_n, 1)]


def get_supplier_sourcing_snapshot(
    session: Session,
    requirements: dict[str, object],
    *,
    top_n: int = DEFAULT_SHORTLIST_TOP_N,
) -> dict[str, object]:
    context = build_context_from_requirements(requirements)
    ranked = rank_suppliers_for_context(session, context, top_n=top_n)
    registry_count = int(session.scalar(select(func.count()).select_from(SupplierProfile)) or 0)
    vendor_list_count = int(
        session.scalar(
            select(func.count(distinct(SupplierTag.supplier_id))).where(SupplierTag.tag_code == "SOURCE_VENDOR_LIST")
        )
        or 0
    )
    return {
        "registry_supplier_count": registry_count,
        "vendor_list_supplier_count": vendor_list_count,
        "top_suppliers": [
            {
                "supplier_id": item.supplier.supplier_id,
                "display_name": item.supplier.display_name,
                "inclusion_reason": item.inclusion_reason,
                "source_type": item.source_type,
            }
            for item in ranked
        ],
    }


def _get_shortlist(session: Session, supplier_shortlist_id: str) -> SupplierShortlist:
    shortlist = session.scalar(
        select(SupplierShortlist).where(SupplierShortlist.supplier_shortlist_id == supplier_shortlist_id)
    )
    if not shortlist:
        raise NotFoundError(f"Supplier shortlist '{supplier_shortlist_id}' was not found")
    return shortlist


def _get_shortlist_rows(session: Session, supplier_shortlist_id: str) -> list[SupplierShortlistRow]:
    return list(
        session.scalars(
            select(SupplierShortlistRow)
            .where(SupplierShortlistRow.supplier_shortlist_id == supplier_shortlist_id)
            .order_by(SupplierShortlistRow.rank_order.asc(), SupplierShortlistRow.id.asc())
        )
    )


def build_supplier_shortlist(session: Session, payload: BuildSupplierShortlistRequest) -> SupplierShortlist:
    package = load_analysis_package(
        session,
        deal_id=payload.deal_id,
        intake_id=payload.intake_id,
        document_set_id=payload.document_set_id,
        tender_summary_id=payload.tender_summary_id,
        compliance_matrix_id=payload.compliance_matrix_id,
        document_requirement_set_id=payload.document_requirement_set_id,
        risk_flag_set_id=payload.risk_flag_set_id,
    )
    shortlist = SupplierShortlist(
        supplier_shortlist_id=next_supplier_shortlist_id(session, SupplierShortlist.supplier_shortlist_id),
        deal_id=package.deal_id,
        intake_id=package.intake.intake_id,
        document_set_id=package.document_set.document_set_id,
        tender_summary_id=package.tender_summary.tender_summary_id,
        shortlist_status=SupplierShortlistStatus.BUILT,
    )
    session.add(shortlist)
    session.flush()
    append_event_record(
        session,
        deal_id=package.deal_id,
        event_code="supplier_shortlist_build_started",
        source_module_id="M-016",
        severity=EventSeverity.INFO,
        payload_json={"supplier_shortlist_id": shortlist.supplier_shortlist_id},
    )
    try:
        ranked = rank_suppliers_for_context(session, _build_context_from_package(package), top_n=payload.top_n or DEFAULT_SHORTLIST_TOP_N)
        if not ranked:
            shortlist.shortlist_status = SupplierShortlistStatus.FAILED
            shortlist.updated_at = utcnow()
            session.add(shortlist)
            append_event_record(
                session,
                deal_id=package.deal_id,
                event_code="supplier_shortlist_failed",
                source_module_id="M-016",
                severity=EventSeverity.HIGH,
                payload_json={
                    "supplier_shortlist_id": shortlist.supplier_shortlist_id,
                    "reason": "NO_ACTIVE_SUPPLIERS",
                },
            )
            session.commit()
            session.refresh(shortlist)
            return shortlist

        for index, ranked_item in enumerate(ranked, start=1):
            session.add(
                SupplierShortlistRow(
                    supplier_shortlist_id=shortlist.supplier_shortlist_id,
                    supplier_id=ranked_item.supplier.supplier_id,
                    rank_order=index,
                    inclusion_reason=ranked_item.inclusion_reason,
                    source_type=ranked_item.source_type,
                )
            )
        shortlist.updated_at = utcnow()
        session.add(shortlist)
        append_event_record(
            session,
            deal_id=package.deal_id,
            event_code="supplier_shortlist_built",
            source_module_id="M-016",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_shortlist_id": shortlist.supplier_shortlist_id,
                "row_count": len(ranked),
            },
        )
        session.commit()
    except Exception as exc:
        shortlist.shortlist_status = SupplierShortlistStatus.FAILED
        shortlist.updated_at = utcnow()
        session.add(shortlist)
        append_event_record(
            session,
            deal_id=package.deal_id,
            event_code="supplier_shortlist_failed",
            source_module_id="M-016",
            severity=EventSeverity.HIGH,
            payload_json={"supplier_shortlist_id": shortlist.supplier_shortlist_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(shortlist)
    return shortlist


def get_supplier_shortlist(session: Session, supplier_shortlist_id: str) -> tuple[SupplierShortlist, list[SupplierShortlistRow]]:
    shortlist = _get_shortlist(session, supplier_shortlist_id)
    return shortlist, _get_shortlist_rows(session, supplier_shortlist_id)


def list_supplier_shortlists(session: Session, *, deal_id: str | None = None) -> list[tuple[SupplierShortlist, list[SupplierShortlistRow]]]:
    query = select(SupplierShortlist).order_by(SupplierShortlist.created_at.desc())
    if deal_id:
        query = query.where(SupplierShortlist.deal_id == deal_id)
    records = list(session.scalars(query))
    return [(record, _get_shortlist_rows(session, record.supplier_shortlist_id)) for record in records]
