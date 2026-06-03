from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.supplier_registry.models import SupplierContact, SupplierExternalRef, SupplierProfile, SupplierTag
from src.modules.supplier_registry.schemas import (
    CreateSupplierContactRequest,
    CreateSupplierRequest,
    CreateSupplierTagRequest,
    UpdateSupplierRequest,
)
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity
from src.shared.errors import NotFoundError
from src.shared.ids import next_supplier_id
from src.shared.validation import require_non_empty


def _get_supplier_profile(session: Session, supplier_id: str) -> SupplierProfile:
    supplier = session.scalar(select(SupplierProfile).where(SupplierProfile.supplier_id == supplier_id))
    if not supplier:
        raise NotFoundError(f"Supplier '{supplier_id}' was not found")
    return supplier


def _get_supplier_contacts(session: Session, supplier_id: str) -> list[SupplierContact]:
    return list(
        session.scalars(
            select(SupplierContact)
            .where(SupplierContact.supplier_id == supplier_id)
            .order_by(SupplierContact.is_primary.desc(), SupplierContact.created_at.asc(), SupplierContact.id.asc())
        )
    )


def _get_supplier_tags(session: Session, supplier_id: str) -> list[SupplierTag]:
    return list(
        session.scalars(
            select(SupplierTag)
            .where(SupplierTag.supplier_id == supplier_id)
            .order_by(SupplierTag.created_at.asc(), SupplierTag.id.asc())
        )
    )


def _get_supplier_external_refs(session: Session, supplier_id: str) -> list[SupplierExternalRef]:
    return list(
        session.scalars(
            select(SupplierExternalRef)
            .where(SupplierExternalRef.supplier_id == supplier_id)
            .order_by(SupplierExternalRef.created_at.asc(), SupplierExternalRef.id.asc())
        )
    )


def create_supplier(session: Session, payload: CreateSupplierRequest) -> tuple[SupplierProfile, bool]:
    existing = session.scalar(select(SupplierProfile).where(SupplierProfile.inn == require_non_empty(payload.inn, "inn")))
    if existing:
        return existing, True

    supplier = SupplierProfile(
        supplier_id=next_supplier_id(session, SupplierProfile.supplier_id),
        legal_name=require_non_empty(payload.legal_name, "legal_name"),
        display_name=require_non_empty(payload.display_name, "display_name"),
        inn=require_non_empty(payload.inn, "inn"),
        country_code=require_non_empty(payload.country_code, "country_code").upper(),
        status=payload.status,
        notes=payload.notes.strip() if payload.notes else None,
    )
    session.add(supplier)
    session.flush()
    append_event_record(
        session,
        deal_id=None,
        event_code="supplier_profile_created",
        source_module_id="M-006",
        severity=EventSeverity.INFO,
        payload_json={"supplier_id": supplier.supplier_id, "inn": supplier.inn},
    )
    session.commit()
    session.refresh(supplier)
    return supplier, False


def get_supplier(session: Session, supplier_id: str) -> tuple[SupplierProfile, list[SupplierExternalRef], list[SupplierContact], list[SupplierTag]]:
    supplier = _get_supplier_profile(session, supplier_id)
    return supplier, _get_supplier_external_refs(session, supplier_id), _get_supplier_contacts(session, supplier_id), _get_supplier_tags(session, supplier_id)


def list_suppliers(
    session: Session,
    *,
    q: str | None = None,
    inn: str | None = None,
    status: str | None = None,
) -> list[tuple[SupplierProfile, list[SupplierExternalRef], list[SupplierContact], list[SupplierTag]]]:
    query = select(SupplierProfile).order_by(SupplierProfile.created_at.desc())
    if inn:
        query = query.where(SupplierProfile.inn == inn.strip())
    if status:
        query = query.where(SupplierProfile.status == status)
    if q:
        pattern = f"%{q.strip()}%"
        query = query.where(or_(SupplierProfile.legal_name.ilike(pattern), SupplierProfile.display_name.ilike(pattern)))
    suppliers = list(session.scalars(query))
    return [(supplier, _get_supplier_external_refs(session, supplier.supplier_id), _get_supplier_contacts(session, supplier.supplier_id), _get_supplier_tags(session, supplier.supplier_id)) for supplier in suppliers]


def update_supplier(session: Session, supplier_id: str, payload: UpdateSupplierRequest) -> SupplierProfile:
    supplier = _get_supplier_profile(session, supplier_id)
    updated_fields: dict[str, str] = {}
    if payload.legal_name is not None:
        supplier.legal_name = require_non_empty(payload.legal_name, "legal_name")
        updated_fields["legal_name"] = supplier.legal_name
    if payload.display_name is not None:
        supplier.display_name = require_non_empty(payload.display_name, "display_name")
        updated_fields["display_name"] = supplier.display_name
    if payload.country_code is not None:
        supplier.country_code = require_non_empty(payload.country_code, "country_code").upper()
        updated_fields["country_code"] = supplier.country_code
    if payload.status is not None:
        supplier.status = payload.status
        updated_fields["status"] = str(payload.status)
    if payload.notes is not None:
        supplier.notes = payload.notes.strip() if payload.notes else None
        updated_fields["notes"] = supplier.notes or ""
    if updated_fields:
        supplier.updated_at = utcnow()
        session.add(supplier)
        append_event_record(
            session,
            deal_id=None,
            event_code="supplier_profile_updated",
            source_module_id="M-006",
            severity=EventSeverity.INFO,
            payload_json={"supplier_id": supplier.supplier_id, "updated_fields": updated_fields},
        )
        session.commit()
        session.refresh(supplier)
    return supplier


def add_supplier_contact(session: Session, supplier_id: str, payload: CreateSupplierContactRequest) -> SupplierContact:
    supplier = _get_supplier_profile(session, supplier_id)
    if payload.is_primary:
        for existing in _get_supplier_contacts(session, supplier_id):
            if existing.is_primary:
                existing.is_primary = False
                session.add(existing)
    contact = SupplierContact(
        supplier_id=supplier.supplier_id,
        contact_name=require_non_empty(payload.contact_name, "contact_name"),
        email=payload.email.strip() if payload.email else None,
        phone=payload.phone.strip() if payload.phone else None,
        is_primary=payload.is_primary,
    )
    session.add(contact)
    supplier.updated_at = utcnow()
    session.add(supplier)
    session.commit()
    session.refresh(contact)
    return contact


def add_supplier_tag(session: Session, supplier_id: str, payload: CreateSupplierTagRequest) -> SupplierTag:
    supplier = _get_supplier_profile(session, supplier_id)
    tag_code = require_non_empty(payload.tag_code, "tag_code").upper()
    existing = session.scalar(
        select(SupplierTag).where(SupplierTag.supplier_id == supplier.supplier_id, SupplierTag.tag_code == tag_code)
    )
    if existing:
        return existing
    tag = SupplierTag(supplier_id=supplier.supplier_id, tag_code=tag_code)
    session.add(tag)
    supplier.updated_at = utcnow()
    session.add(supplier)
    session.commit()
    session.refresh(tag)
    return tag
