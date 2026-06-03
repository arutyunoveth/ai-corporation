from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.supplier_registry.models import SupplierProfile, SupplierTag
from src.modules.supplier_search.models import SupplierShortlist, SupplierShortlistRow
from src.modules.supplier_search.schemas import BuildSupplierShortlistRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, SupplierShortlistStatus, SupplierStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_supplier_shortlist_id
from src.shared.supplier_package import load_analysis_package


def _tag_set(session: Session, supplier_id: str) -> set[str]:
    return {
        str(tag)
        for tag in session.scalars(select(SupplierTag.tag_code).where(SupplierTag.supplier_id == supplier_id))
    }


def _domain_signal(package) -> str:
    return str(package.deal.domain_type or "").upper()


def _rank_suppliers(session: Session, package) -> list[tuple[SupplierProfile, int, str]]:
    candidates = list(
        session.scalars(
            select(SupplierProfile)
            .where(SupplierProfile.status == SupplierStatus.ACTIVE)
            .order_by(SupplierProfile.created_at.asc(), SupplierProfile.id.asc())
        )
    )
    domain_signal = _domain_signal(package)
    ranked: list[tuple[SupplierProfile, int, str]] = []
    for supplier in candidates:
        score = 0
        reasons: list[str] = []
        tags = _tag_set(session, supplier.supplier_id)
        combined_name = f"{supplier.legal_name} {supplier.display_name}".lower()

        if supplier.country_code == "RU":
            score += 1
            reasons.append("RU registry presence")
        if domain_signal and domain_signal in tags:
            score += 4
            reasons.append(f"tag match {domain_signal}")
        if "ELECTRO" in combined_name or "ЭЛЕКТРО" in combined_name.upper():
            score += 2
            reasons.append("electrical profile keyword")
        if "TENDER_READY" in tags:
            score += 2
            reasons.append("tender-ready tag")
        if package.document_requirement_set and package.document_requirement_set.requirement_count > 0:
            score += 1
            reasons.append("requirements-aware shortlist context")
        if package.risk_flag_set and package.risk_flag_set.risk_flag_count <= 2:
            score += 1
            reasons.append("manageable early technical risk level")
        ranked.append((supplier, score, ", ".join(reasons) if reasons else "Active supplier from reusable registry"))

    ranked.sort(key=lambda item: (-item[1], item[0].created_at, item[0].supplier_id))
    return ranked[:5]


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
        ranked = _rank_suppliers(session, package)
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

        for index, (supplier, _, reason) in enumerate(ranked, start=1):
            session.add(
                SupplierShortlistRow(
                    supplier_shortlist_id=shortlist.supplier_shortlist_id,
                    supplier_id=supplier.supplier_id,
                    rank_order=index,
                    inclusion_reason=reason,
                    source_type="REGISTRY",
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
