from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.modules.customer_registry.models import CustomerContour, CustomerExternalRef, CustomerProfile
from src.modules.customer_registry.schemas import CreateCustomerRequest, UpdateCustomerRequest
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import CustomerStatus, EventSeverity
from src.shared.errors import NotFoundError
from src.shared.ids import next_customer_id
from src.shared.validation import require_non_empty


def _get_customer_profile(session: Session, customer_id: str) -> CustomerProfile:
    profile = session.scalar(select(CustomerProfile).where(CustomerProfile.customer_id == customer_id))
    if not profile:
        raise NotFoundError(f"Customer '{customer_id}' was not found")
    return profile


def _get_customer_external_refs(session: Session, customer_id: str) -> list[CustomerExternalRef]:
    return list(
        session.scalars(
            select(CustomerExternalRef)
            .where(CustomerExternalRef.customer_id == customer_id)
            .order_by(CustomerExternalRef.created_at.asc(), CustomerExternalRef.id.asc())
        )
    )


def _get_customer_contours(session: Session, customer_id: str) -> list[CustomerContour]:
    return list(
        session.scalars(
            select(CustomerContour)
            .where(CustomerContour.customer_id == customer_id)
            .order_by(CustomerContour.created_at.asc(), CustomerContour.id.asc())
        )
    )


def _add_external_ref(session: Session, customer_id: str, source_type: str, source_ref: str) -> None:
    source_type = require_non_empty(source_type, "source_type")
    source_ref = require_non_empty(source_ref, "source_ref")
    existing = session.scalar(
        select(CustomerExternalRef).where(
            CustomerExternalRef.customer_id == customer_id,
            CustomerExternalRef.source_type == source_type,
            CustomerExternalRef.source_ref == source_ref,
        )
    )
    if not existing:
        session.add(CustomerExternalRef(customer_id=customer_id, source_type=source_type, source_ref=source_ref))


def _add_contour(session: Session, customer_id: str, contour_code: str, contour_name: str, notes: str | None) -> None:
    contour_code = require_non_empty(contour_code, "contour_code").upper()
    existing = session.scalar(
        select(CustomerContour).where(
            CustomerContour.customer_id == customer_id,
            CustomerContour.contour_code == contour_code,
        )
    )
    if not existing:
        session.add(
            CustomerContour(
                customer_id=customer_id,
                contour_code=contour_code,
                contour_name=require_non_empty(contour_name, "contour_name"),
                notes=notes.strip() if notes else None,
            )
        )


def create_customer(session: Session, payload: CreateCustomerRequest) -> tuple[CustomerProfile, bool]:
    legal_name = require_non_empty(payload.legal_name, "legal_name")
    inn = payload.inn.strip() if payload.inn else None
    existing = None
    if inn:
        existing = session.scalar(select(CustomerProfile).where(CustomerProfile.inn == inn))
    if not existing:
        existing = session.scalar(select(CustomerProfile).where(CustomerProfile.legal_name == legal_name))
    if existing:
        if payload.deal_id:
            _add_external_ref(session, existing.customer_id, "DEAL", payload.deal_id)
        for ref in payload.external_refs:
            _add_external_ref(session, existing.customer_id, ref.source_type, ref.source_ref)
        for contour in payload.contours:
            _add_contour(session, existing.customer_id, contour.contour_code, contour.contour_name, contour.notes)
        existing.updated_at = utcnow()
        session.add(existing)
        session.commit()
        return existing, True

    profile = CustomerProfile(
        customer_id=next_customer_id(session, CustomerProfile.customer_id),
        legal_name=legal_name,
        inn=inn,
        kpp=payload.kpp.strip() if payload.kpp else None,
        customer_status=payload.customer_status,
    )
    session.add(profile)
    session.flush()

    if payload.deal_id:
        _add_external_ref(session, profile.customer_id, "DEAL", payload.deal_id)
    for ref in payload.external_refs:
        _add_external_ref(session, profile.customer_id, ref.source_type, ref.source_ref)
    for contour in payload.contours:
        _add_contour(session, profile.customer_id, contour.contour_code, contour.contour_name, contour.notes)

    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="customer_profile_created",
        source_module_id="M-005",
        severity=EventSeverity.INFO,
        payload_json={"customer_id": profile.customer_id, "legal_name": profile.legal_name},
    )
    session.commit()
    session.refresh(profile)
    return profile, False


def get_customer(
    session: Session,
    customer_id: str,
) -> tuple[CustomerProfile, list[CustomerExternalRef], list[CustomerContour]]:
    profile = _get_customer_profile(session, customer_id)
    return profile, _get_customer_external_refs(session, customer_id), _get_customer_contours(session, customer_id)


def list_customers(
    session: Session,
    *,
    q: str | None = None,
    inn: str | None = None,
    status: str | None = None,
) -> list[tuple[CustomerProfile, list[CustomerExternalRef], list[CustomerContour]]]:
    query = select(CustomerProfile).order_by(CustomerProfile.created_at.desc())
    if inn:
        query = query.where(CustomerProfile.inn == inn.strip())
    if status:
        query = query.where(CustomerProfile.customer_status == status)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(CustomerProfile.legal_name.ilike(pattern), CustomerProfile.inn.ilike(pattern)))
    profiles = list(session.scalars(query))
    return [(profile, _get_customer_external_refs(session, profile.customer_id), _get_customer_contours(session, profile.customer_id)) for profile in profiles]


def update_customer(session: Session, customer_id: str, payload: UpdateCustomerRequest) -> CustomerProfile:
    profile = _get_customer_profile(session, customer_id)
    updated_fields: dict[str, str] = {}
    if payload.legal_name is not None:
        profile.legal_name = require_non_empty(payload.legal_name, "legal_name")
        updated_fields["legal_name"] = profile.legal_name
    if payload.inn is not None:
        profile.inn = payload.inn.strip() if payload.inn else None
        updated_fields["inn"] = profile.inn or ""
    if payload.kpp is not None:
        profile.kpp = payload.kpp.strip() if payload.kpp else None
        updated_fields["kpp"] = profile.kpp or ""
    if payload.customer_status is not None:
        profile.customer_status = payload.customer_status
        updated_fields["customer_status"] = str(payload.customer_status)
    if updated_fields:
        profile.updated_at = utcnow()
        session.add(profile)
        deal_ref = session.scalar(
            select(CustomerExternalRef).where(
                CustomerExternalRef.customer_id == profile.customer_id,
                CustomerExternalRef.source_type == "DEAL",
            )
        )
        append_event_record(
            session,
            deal_id=deal_ref.source_ref if deal_ref else None,
            event_code="customer_profile_updated",
            source_module_id="M-005",
            severity=EventSeverity.INFO,
            payload_json={"customer_id": profile.customer_id, "updated_fields": updated_fields},
        )
        session.commit()
        session.refresh(profile)
    return profile


def find_or_create_customer(
    session: Session,
    *,
    legal_name: str,
    inn: str | None = None,
    kpp: str | None = None,
    deal_id: str | None = None,
    source_type: str | None = None,
    source_ref: str | None = None,
) -> CustomerProfile:
    profile, _duplicate = create_customer(
        session,
        CreateCustomerRequest(
            legal_name=legal_name,
            inn=inn,
            kpp=kpp,
            customer_status=CustomerStatus.PROSPECT,
            deal_id=deal_id,
            external_refs=[
                {"source_type": source_type, "source_ref": source_ref}
            ]
            if source_type and source_ref
            else [],
        ),
    )
    return profile
