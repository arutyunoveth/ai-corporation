from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.quote_repository.models import QuoteRecord, QuoteSet
from src.modules.supplier_communications.models import SupplierCommunicationThread
from src.modules.supplier_registry.models import SupplierContact, SupplierProfile, SupplierTag
from src.modules.supplier_search.models import SupplierShortlistRow
from src.modules.supplier_verification.models import (
    SupplierVerificationFlag,
    SupplierVerificationRecord,
    SupplierVerificationSet,
)
from src.modules.supplier_verification.schemas import BuildSupplierVerificationRequest
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    QuoteStatus,
    SupplierStatus,
    SupplierVerificationResult,
    SupplierVerificationStatus,
    VerificationFlagSeverity,
)
from src.shared.errors import NotFoundError
from src.shared.ids import next_supplier_verification_id, next_supplier_verification_set_id
from src.shared.quality_package import load_supplier_quality_package
from src.shared.validation import require_same_reference


def _get_set(session: Session, supplier_verification_set_id: str) -> SupplierVerificationSet:
    record = session.scalar(
        select(SupplierVerificationSet).where(
            SupplierVerificationSet.supplier_verification_set_id == supplier_verification_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Supplier verification set '{supplier_verification_set_id}' was not found")
    return record


def _get_record(session: Session, supplier_verification_id: str) -> SupplierVerificationRecord:
    record = session.scalar(
        select(SupplierVerificationRecord).where(
            SupplierVerificationRecord.supplier_verification_id == supplier_verification_id
        )
    )
    if not record:
        raise NotFoundError(f"Supplier verification record '{supplier_verification_id}' was not found")
    return record


def _get_flags(session: Session, supplier_verification_id: str) -> list[SupplierVerificationFlag]:
    return list(
        session.scalars(
            select(SupplierVerificationFlag)
            .where(SupplierVerificationFlag.supplier_verification_id == supplier_verification_id)
            .order_by(SupplierVerificationFlag.created_at.asc(), SupplierVerificationFlag.id.asc())
        )
    )


def _get_records(session: Session, supplier_verification_set_id: str) -> list[SupplierVerificationRecord]:
    return list(
        session.scalars(
            select(SupplierVerificationRecord)
            .where(SupplierVerificationRecord.supplier_verification_set_id == supplier_verification_set_id)
            .order_by(SupplierVerificationRecord.created_at.asc(), SupplierVerificationRecord.id.asc())
        )
    )


def _supplier_contacts(session: Session, supplier_id: str) -> list[SupplierContact]:
    return list(
        session.scalars(
            select(SupplierContact)
            .where(SupplierContact.supplier_id == supplier_id)
            .order_by(SupplierContact.is_primary.desc(), SupplierContact.created_at.asc())
        )
    )


def _supplier_tags(session: Session, supplier_id: str) -> set[str]:
    return {
        str(tag)
        for tag in session.scalars(select(SupplierTag.tag_code).where(SupplierTag.supplier_id == supplier_id))
    }


def _latest_thread(session: Session, deal_id: str, supplier_id: str) -> SupplierCommunicationThread | None:
    return session.scalar(
        select(SupplierCommunicationThread)
        .join(
            QuoteRecord,
            QuoteRecord.supplier_thread_id == SupplierCommunicationThread.supplier_thread_id,
            isouter=True,
        )
        .join(QuoteSet, QuoteSet.quote_set_id == QuoteRecord.quote_set_id, isouter=True)
        .where(
            SupplierCommunicationThread.supplier_id == supplier_id,
            (QuoteSet.deal_id == deal_id) | (QuoteSet.deal_id.is_(None)),
        )
        .order_by(SupplierCommunicationThread.created_at.desc(), SupplierCommunicationThread.id.desc())
        .limit(1)
    )


def _latest_quote(session: Session, deal_id: str, supplier_id: str) -> QuoteRecord | None:
    return session.scalar(
        select(QuoteRecord)
        .join(QuoteSet, QuoteSet.quote_set_id == QuoteRecord.quote_set_id)
        .where(QuoteSet.deal_id == deal_id, QuoteRecord.supplier_id == supplier_id)
        .order_by(QuoteRecord.created_at.desc(), QuoteRecord.id.desc())
        .limit(1)
    )


def _build_verification_for_supplier(session: Session, deal_id: str, row: SupplierShortlistRow) -> tuple[dict, list[dict]]:
    supplier = session.scalar(select(SupplierProfile).where(SupplierProfile.supplier_id == row.supplier_id))
    if not supplier:
        raise NotFoundError(f"Supplier '{row.supplier_id}' was not found")

    contacts = _supplier_contacts(session, supplier.supplier_id)
    tags = _supplier_tags(session, supplier.supplier_id)
    latest_quote = _latest_quote(session, deal_id, supplier.supplier_id)
    latest_thread = _latest_thread(session, deal_id, supplier.supplier_id)

    flags: list[dict] = []
    confidence = 1.0

    if supplier.status == SupplierStatus.BLACKLISTED:
        flags.append(
            {
                "flag_code": "BLACKLISTED_SUPPLIER",
                "severity": VerificationFlagSeverity.CRITICAL,
                "summary": "Supplier is marked as blacklisted in the reusable registry.",
                "source_ref": f"SUPPLIER:{supplier.supplier_id}",
            }
        )
        confidence -= 0.75
    elif supplier.status != SupplierStatus.ACTIVE:
        flags.append(
            {
                "flag_code": "NON_ACTIVE_SUPPLIER",
                "severity": VerificationFlagSeverity.HIGH,
                "summary": "Supplier status is not ACTIVE and needs review before award path.",
                "source_ref": f"SUPPLIER:{supplier.supplier_id}",
            }
        )
        confidence -= 0.35

    primary_contact = next((contact for contact in contacts if contact.is_primary), None)
    if not primary_contact:
        flags.append(
            {
                "flag_code": "MISSING_PRIMARY_CONTACT",
                "severity": VerificationFlagSeverity.MEDIUM,
                "summary": "Supplier has no primary contact in the registry.",
                "source_ref": f"SUPPLIER:{supplier.supplier_id}",
            }
        )
        confidence -= 0.2
    elif not primary_contact.email:
        flags.append(
            {
                "flag_code": "MISSING_CONTACT_EMAIL",
                "severity": VerificationFlagSeverity.LOW,
                "summary": "Primary supplier contact has no email registered.",
                "source_ref": f"SUPPLIER_CONTACT:{primary_contact.id}",
            }
        )
        confidence -= 0.1

    if "TENDER_READY" not in tags:
        flags.append(
            {
                "flag_code": "NO_TENDER_READY_TAG",
                "severity": VerificationFlagSeverity.LOW,
                "summary": "Supplier is not explicitly marked as tender-ready in registry tags.",
                "source_ref": f"SUPPLIER:{supplier.supplier_id}",
            }
        )
        confidence -= 0.1

    if supplier.country_code != "RU":
        flags.append(
            {
                "flag_code": "NON_RU_SUPPLIER",
                "severity": VerificationFlagSeverity.MEDIUM,
                "summary": "Supplier is registered outside RU and needs additional manual review.",
                "source_ref": f"SUPPLIER:{supplier.supplier_id}",
            }
        )
        confidence -= 0.15

    if latest_thread is None:
        flags.append(
            {
                "flag_code": "NO_COMMUNICATION_THREAD",
                "severity": VerificationFlagSeverity.LOW,
                "summary": "No persisted supplier communication thread exists yet for this deal context.",
                "source_ref": f"SUPPLIER_SHORTLIST:{row.supplier_shortlist_id}:{supplier.supplier_id}",
            }
        )
        confidence -= 0.05

    if latest_quote and latest_quote.quote_status == QuoteStatus.WITHDRAWN:
        flags.append(
            {
                "flag_code": "QUOTE_WITHDRAWN",
                "severity": VerificationFlagSeverity.HIGH,
                "summary": "Latest supplier quote was withdrawn.",
                "source_ref": f"QUOTE:{latest_quote.quote_id}",
            }
        )
        confidence -= 0.4

    confidence_score = round(max(0.05, min(0.99, confidence)), 4)
    severe_codes = {flag["flag_code"] for flag in flags}
    if "BLACKLISTED_SUPPLIER" in severe_codes or "QUOTE_WITHDRAWN" in severe_codes:
        result = SupplierVerificationResult.FAIL
    elif any(flag["severity"] in {VerificationFlagSeverity.MEDIUM, VerificationFlagSeverity.HIGH} for flag in flags):
        result = SupplierVerificationResult.NEEDS_REVIEW
    else:
        result = SupplierVerificationResult.PASS

    notes = f"Verification built from supplier registry, communication, and quote context. Confidence={confidence_score:.2f}."
    record_data = {
        "supplier_id": supplier.supplier_id,
        "verification_result": result,
        "confidence_score": confidence_score,
        "notes": notes,
    }
    return record_data, flags


def build_supplier_verification(session: Session, payload: BuildSupplierVerificationRequest) -> SupplierVerificationSet:
    package = load_supplier_quality_package(
        session,
        deal_id=payload.deal_id,
        supplier_shortlist_id=payload.supplier_shortlist_id,
    )
    verification_set = SupplierVerificationSet(
        supplier_verification_set_id=next_supplier_verification_set_id(
            session, SupplierVerificationSet.supplier_verification_set_id
        ),
        deal_id=payload.deal_id,
        supplier_shortlist_id=package.shortlist.supplier_shortlist_id,
        verification_status=SupplierVerificationStatus.BUILT,
    )
    session.add(verification_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="supplier_verification_build_started",
        source_module_id="M-020",
        severity=EventSeverity.INFO,
        payload_json={
            "supplier_verification_set_id": verification_set.supplier_verification_set_id,
            "supplier_shortlist_id": package.shortlist.supplier_shortlist_id,
        },
    )
    try:
        if not package.shortlist_rows:
            verification_set.verification_status = SupplierVerificationStatus.FAILED
            verification_set.updated_at = utcnow()
            session.add(verification_set)
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="supplier_verification_failed",
                source_module_id="M-020",
                severity=EventSeverity.HIGH,
                payload_json={
                    "supplier_verification_set_id": verification_set.supplier_verification_set_id,
                    "reason": "EMPTY_SHORTLIST",
                },
            )
            session.commit()
            session.refresh(verification_set)
            return verification_set

        results: list[str] = []
        for row in package.shortlist_rows:
            record_data, flags_data = _build_verification_for_supplier(session, payload.deal_id, row)
            verification = SupplierVerificationRecord(
                supplier_verification_id=next_supplier_verification_id(
                    session, SupplierVerificationRecord.supplier_verification_id
                ),
                supplier_verification_set_id=verification_set.supplier_verification_set_id,
                **record_data,
            )
            session.add(verification)
            session.flush()
            for flag_data in flags_data:
                session.add(SupplierVerificationFlag(supplier_verification_id=verification.supplier_verification_id, **flag_data))
            results.append(str(verification.verification_result))

        if any(result == SupplierVerificationResult.FAIL for result in results):
            verification_set.verification_status = SupplierVerificationStatus.PARTIAL
        elif any(result == SupplierVerificationResult.NEEDS_REVIEW for result in results):
            verification_set.verification_status = SupplierVerificationStatus.PARTIAL
        else:
            verification_set.verification_status = SupplierVerificationStatus.BUILT
        verification_set.updated_at = utcnow()
        session.add(verification_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_verification_built",
            source_module_id="M-020",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_verification_set_id": verification_set.supplier_verification_set_id,
                "record_count": len(results),
                "verification_status": str(verification_set.verification_status),
            },
        )
        session.commit()
    except Exception as exc:
        verification_set.verification_status = SupplierVerificationStatus.FAILED
        verification_set.updated_at = utcnow()
        session.add(verification_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_verification_failed",
            source_module_id="M-020",
            severity=EventSeverity.HIGH,
            payload_json={
                "supplier_verification_set_id": verification_set.supplier_verification_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise
    session.refresh(verification_set)
    return verification_set


def get_supplier_verification_set(
    session: Session, supplier_verification_set_id: str
) -> tuple[SupplierVerificationSet, list[tuple[SupplierVerificationRecord, list[SupplierVerificationFlag]]]]:
    verification_set = _get_set(session, supplier_verification_set_id)
    records = _get_records(session, supplier_verification_set_id)
    return verification_set, [(record, _get_flags(session, record.supplier_verification_id)) for record in records]


def list_supplier_verification_sets(
    session: Session, *, deal_id: str | None = None
) -> list[tuple[SupplierVerificationSet, list[tuple[SupplierVerificationRecord, list[SupplierVerificationFlag]]]]]:
    query = select(SupplierVerificationSet).order_by(SupplierVerificationSet.created_at.desc())
    if deal_id:
        query = query.where(SupplierVerificationSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_supplier_verification_set(session, item.supplier_verification_set_id) for item in sets]


def get_supplier_verification_record(
    session: Session, supplier_verification_id: str
) -> tuple[SupplierVerificationRecord, list[SupplierVerificationFlag]]:
    record = _get_record(session, supplier_verification_id)
    return record, _get_flags(session, supplier_verification_id)
