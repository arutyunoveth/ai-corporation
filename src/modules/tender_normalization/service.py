from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.customer_registry.service import find_or_create_customer
from src.modules.deal_registry.models import Deal
from src.modules.event_log.service import append_event_record
from src.modules.tender_import.models import TenderImportRun
from src.modules.tender_import.service import get_tender_import_event
from src.modules.tender_intake.schemas import CreateTenderIntakeRequest
from src.modules.tender_intake.service import (
    _create_new_deal,
    _find_duplicate_deal_id,
    _link_source_refs,
    _sync_deal_metadata_from_intake,
)
from src.modules.tender_intake.models import TenderIntakeRecord, TenderSourcePayload
from src.modules.tender_normalization.models import (
    TenderNormalizationLink,
    TenderNormalizationRecord,
    TenderNormalizationSet,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    DirectionType,
    EventSeverity,
    InitialSourceType,
    IntakeStatus,
    TenderNormalizationStatus,
    TenderSourceType,
)
from src.shared.errors import NotFoundError
from src.shared.ids import (
    next_intake_id,
    next_tender_normalization_id,
    next_tender_normalization_set_id,
)
from src.shared.validation import compute_payload_hash


def _get_set(session: Session, tender_normalization_set_id: str) -> TenderNormalizationSet:
    record = session.scalar(
        select(TenderNormalizationSet).where(
            TenderNormalizationSet.tender_normalization_set_id == tender_normalization_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Tender normalization set '{tender_normalization_set_id}' was not found")
    return record


def _get_record(session: Session, tender_normalization_id: str) -> TenderNormalizationRecord:
    record = session.scalar(
        select(TenderNormalizationRecord).where(
            TenderNormalizationRecord.tender_normalization_id == tender_normalization_id
        )
    )
    if not record:
        raise NotFoundError(f"Tender normalization record '{tender_normalization_id}' was not found")
    return record


def _get_records(session: Session, tender_normalization_set_id: str) -> list[TenderNormalizationRecord]:
    return list(
        session.scalars(
            select(TenderNormalizationRecord)
            .where(TenderNormalizationRecord.tender_normalization_set_id == tender_normalization_set_id)
            .order_by(TenderNormalizationRecord.created_at.asc(), TenderNormalizationRecord.id.asc())
        )
    )


def _get_links(session: Session, tender_normalization_id: str) -> list[TenderNormalizationLink]:
    return list(
        session.scalars(
            select(TenderNormalizationLink)
            .where(TenderNormalizationLink.tender_normalization_id == tender_normalization_id)
            .order_by(TenderNormalizationLink.created_at.asc(), TenderNormalizationLink.id.asc())
        )
    )


def _first_non_empty(*values) -> str | None:
    for value in values:
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    try:
        if normalized.endswith("Z"):
            normalized = normalized.replace("Z", "+00:00")
        if "T" not in normalized and len(normalized) == 10:
            normalized = f"{normalized}T00:00:00+00:00"
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _map_source_type(source_type: str) -> TenderSourceType:
    normalized = source_type.upper()
    if normalized in {"EIS", "ETP", "PORTAL"}:
        return TenderSourceType.PORTAL
    if normalized in {"API"}:
        return TenderSourceType.API
    if normalized in {"EMAIL"}:
        return TenderSourceType.EMAIL
    if normalized in {"MANUAL"}:
        return TenderSourceType.MANUAL
    return TenderSourceType.OTHER


def _materialize_legacy_intake(
    session: Session,
    *,
    source_type: str,
    source_ref: str,
    normalized_title: str,
    normalized_customer_name: str,
    normalized_procurement_number: str | None,
    payload_json: dict,
) -> str:
    intake_payload = CreateTenderIntakeRequest(
        source_type=_map_source_type(source_type),
        source_channel="canonical_m007_import",
        source_title=normalized_title,
        source_customer_name=normalized_customer_name,
        source_procurement_number=normalized_procurement_number,
        payload_json=payload_json,
        initial_source_type=InitialSourceType.PORTAL_INGEST if _map_source_type(source_type) == TenderSourceType.PORTAL else InitialSourceType.OTHER,
        direction_type=DirectionType.SUPPLY,
        domain_type=_first_non_empty(payload_json.get("domain_type"), payload_json.get("category"), "RECOVERY_IMPORTED"),
    )
    payload_hash = compute_payload_hash(intake_payload.payload_json)
    existing_deal_id, duplicate_hint = _find_duplicate_deal_id(
        session,
        source_type=intake_payload.source_type,
        source_procurement_number=intake_payload.source_procurement_number,
        payload_hash=payload_hash,
    )
    deal = (
        session.scalar(select(Deal).where(Deal.deal_id == existing_deal_id, Deal.is_deleted.is_(False)))
        if existing_deal_id
        else None
    )
    if not deal:
        deal = _create_new_deal(session, intake_payload)

    intake = TenderIntakeRecord(
        intake_id=next_intake_id(session, TenderIntakeRecord.intake_id),
        deal_id=deal.deal_id,
        source_type=intake_payload.source_type,
        source_channel=intake_payload.source_channel,
        source_title=intake_payload.source_title,
        source_customer_name=intake_payload.source_customer_name,
        source_procurement_number=intake_payload.source_procurement_number,
        intake_status=IntakeStatus.LINKED,
        duplicate_hint=duplicate_hint,
        received_at=utcnow(),
        normalized_at=utcnow(),
    )
    session.add(intake)
    session.flush()
    session.add(
        TenderSourcePayload(
            intake_id=intake.intake_id,
            payload_json=intake_payload.payload_json,
            payload_hash=payload_hash,
        )
    )
    _sync_deal_metadata_from_intake(session, deal, intake_payload)
    _link_source_refs(session, deal, intake_payload)
    return deal.deal_id


def build_tender_normalization(session: Session, tender_import_event_id: str) -> TenderNormalizationSet:
    import_event, payload = get_tender_import_event(session, tender_import_event_id)
    import_run = session.scalar(
        select(TenderImportRun).where(TenderImportRun.tender_import_run_id == import_event.tender_import_run_id)
    )
    normalization_set = TenderNormalizationSet(
        tender_normalization_set_id=next_tender_normalization_set_id(
            session, TenderNormalizationSet.tender_normalization_set_id
        ),
        tender_import_event_id=import_event.tender_import_event_id,
        normalization_status=TenderNormalizationStatus.BUILT,
    )
    session.add(normalization_set)
    session.flush()
    try:
        normalized_procurement_number = _first_non_empty(
            payload.payload_json.get("procurement_number"),
            payload.payload_json.get("notice_number"),
            import_event.raw_procurement_number,
        )
        normalized_title = _first_non_empty(
            payload.payload_json.get("title"),
            payload.payload_json.get("subject"),
            payload.payload_json.get("name"),
            f"Imported tender {import_event.tender_import_event_id}",
        )
        normalized_customer_name = _first_non_empty(
            payload.payload_json.get("customer_name"),
            payload.payload_json.get("customer_legal_name"),
            payload.payload_json.get("organization_name"),
            "Неизвестный заказчик",
        )
        normalized_deadline_at = _parse_dt(
            _first_non_empty(
                payload.payload_json.get("deadline_at"),
                payload.payload_json.get("submission_deadline"),
                payload.payload_json.get("end_date"),
            )
        )

        record = TenderNormalizationRecord(
            tender_normalization_id=next_tender_normalization_id(
                session, TenderNormalizationRecord.tender_normalization_id
            ),
            tender_normalization_set_id=normalization_set.tender_normalization_set_id,
            normalized_procurement_number=normalized_procurement_number,
            normalized_title=normalized_title,
            normalized_customer_name=normalized_customer_name,
            normalized_deadline_at=normalized_deadline_at,
        )
        session.add(record)
        session.flush()

        deal_id = _materialize_legacy_intake(
            session,
            source_type=import_run.source_type if import_run else payload.payload_json.get("source_type", "PORTAL"),
            source_ref=(import_run.source_ref if import_run else None) or import_event.source_url or "",
            normalized_title=normalized_title,
            normalized_customer_name=normalized_customer_name,
            normalized_procurement_number=normalized_procurement_number,
            payload_json=payload.payload_json,
        )
        customer = find_or_create_customer(
            session,
            legal_name=normalized_customer_name,
            inn=_first_non_empty(payload.payload_json.get("customer_inn"), payload.payload_json.get("inn")),
            kpp=_first_non_empty(payload.payload_json.get("customer_kpp"), payload.payload_json.get("kpp")),
            deal_id=deal_id,
            source_type="IMPORT_EVENT",
            source_ref=import_event.tender_import_event_id,
        )
        session.add(
            TenderNormalizationLink(
                tender_normalization_id=record.tender_normalization_id,
                customer_id=customer.customer_id,
                deal_id=deal_id,
            )
        )

        append_event_record(
            session,
            deal_id=deal_id,
            event_code="tender_normalization_built",
            source_module_id="M-008",
            severity=EventSeverity.INFO,
            payload_json={
                "tender_normalization_set_id": normalization_set.tender_normalization_set_id,
                "tender_normalization_id": record.tender_normalization_id,
                "tender_import_event_id": import_event.tender_import_event_id,
            },
        )
        session.commit()
        session.refresh(normalization_set)
        return normalization_set
    except Exception as exc:
        normalization_set.normalization_status = TenderNormalizationStatus.FAILED
        normalization_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=None,
            event_code="tender_normalization_failed",
            source_module_id="M-008",
            severity=EventSeverity.HIGH,
            payload_json={
                "tender_normalization_set_id": normalization_set.tender_normalization_set_id,
                "tender_import_event_id": import_event.tender_import_event_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise


def get_tender_normalization_set(
    session: Session,
    tender_normalization_set_id: str,
) -> tuple[TenderNormalizationSet, list[tuple[TenderNormalizationRecord, list[TenderNormalizationLink]]]]:
    normalization_set = _get_set(session, tender_normalization_set_id)
    records = [(record, _get_links(session, record.tender_normalization_id)) for record in _get_records(session, normalization_set.tender_normalization_set_id)]
    return normalization_set, records


def get_tender_normalization_record(
    session: Session,
    tender_normalization_id: str,
) -> tuple[TenderNormalizationRecord, list[TenderNormalizationLink]]:
    record = _get_record(session, tender_normalization_id)
    return record, _get_links(session, record.tender_normalization_id)


def list_tender_normalization_sets(
    session: Session,
) -> list[tuple[TenderNormalizationSet, list[tuple[TenderNormalizationRecord, list[TenderNormalizationLink]]]]]:
    sets = list(
        session.scalars(
            select(TenderNormalizationSet).order_by(
                TenderNormalizationSet.created_at.desc(),
                TenderNormalizationSet.id.desc(),
            )
        )
    )
    return [get_tender_normalization_set(session, item.tender_normalization_set_id) for item in sets]
