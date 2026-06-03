from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.deal_registry.models import Deal, DealExternalRef
from src.modules.event_log.service import append_event_record
from src.modules.status_engine.service import append_initial_status_history
from src.modules.tender_intake.models import TenderIntakeRecord, TenderSourcePayload
from src.modules.tender_intake.schemas import CreateTenderIntakeRequest
from src.shared.db.base import utcnow
from src.shared.enums import DealStatus, EventSeverity, IntakeStatus, ProcurementChannel, TenderSourceType
from src.shared.errors import NotFoundError
from src.shared.ids import next_deal_id, next_intake_id
from src.shared.validation import compute_payload_hash, require_non_empty


def _map_procurement_channel(source_type: TenderSourceType) -> ProcurementChannel | None:
    mapping = {
        TenderSourceType.PORTAL: ProcurementChannel.PORTAL,
        TenderSourceType.EMAIL: ProcurementChannel.EMAIL,
        TenderSourceType.MANUAL: ProcurementChannel.MANUAL,
        TenderSourceType.API: ProcurementChannel.OTHER,
        TenderSourceType.OTHER: ProcurementChannel.OTHER,
    }
    return mapping.get(source_type)


def _create_new_deal(session: Session, payload: CreateTenderIntakeRequest) -> Deal:
    deal = Deal(
        deal_id=next_deal_id(session, Deal.deal_id),
        title=require_non_empty(payload.source_title, "source_title"),
        customer_name=require_non_empty(payload.source_customer_name, "source_customer_name"),
        procurement_number=payload.source_procurement_number,
        procurement_channel=_map_procurement_channel(payload.source_type),
        initial_source_type=payload.initial_source_type,
        direction_type=payload.direction_type,
        domain_type=require_non_empty(payload.domain_type, "domain_type"),
        current_status=DealStatus.NEW,
    )
    session.add(deal)
    session.flush()
    append_initial_status_history(session, deal_id=deal.deal_id, to_status=DealStatus.NEW)
    append_event_record(
        session,
        deal_id=deal.deal_id,
        event_code="deal_created",
        source_module_id="M-001",
        severity=EventSeverity.INFO,
        payload_json={"title": deal.title, "created_by": "M-008"},
    )
    return deal


def _create_external_ref_if_missing(session: Session, deal_id: str, ref_type: str, ref_value: str) -> None:
    existing = session.scalar(
        select(DealExternalRef).where(
            DealExternalRef.deal_id == deal_id,
            DealExternalRef.ref_type == ref_type,
            DealExternalRef.ref_value == ref_value,
        )
    )
    if existing:
        return
    session.add(DealExternalRef(deal_id=deal_id, ref_type=ref_type, ref_value=ref_value))


def _link_source_refs(session: Session, deal: Deal, payload: CreateTenderIntakeRequest) -> None:
    if payload.source_procurement_number:
        _create_external_ref_if_missing(session, deal.deal_id, "PROCUREMENT_NUMBER", payload.source_procurement_number)
    ref_mapping = {
        "portal_url": "PORTAL_URL",
        "notice_url": "NOTICE_URL",
        "etp_id": "ETP_ID",
        "source_record_id": "INTERNAL_IMPORT_ID",
    }
    for payload_key, ref_type in ref_mapping.items():
        ref_value = payload.payload_json.get(payload_key)
        if isinstance(ref_value, str) and ref_value.strip():
            _create_external_ref_if_missing(session, deal.deal_id, ref_type, ref_value.strip())


def _find_duplicate_deal_id(
    session: Session,
    *,
    source_type: TenderSourceType,
    source_procurement_number: str | None,
    payload_hash: str,
) -> tuple[str | None, bool]:
    if source_procurement_number:
        existing_intake = session.scalar(
            select(TenderIntakeRecord)
            .where(
                TenderIntakeRecord.source_type == source_type,
                TenderIntakeRecord.source_procurement_number == source_procurement_number,
            )
            .order_by(TenderIntakeRecord.created_at.desc())
            .limit(1)
        )
        if existing_intake:
            return existing_intake.deal_id, True

    existing_payload = session.scalar(
        select(TenderSourcePayload)
        .where(TenderSourcePayload.payload_hash == payload_hash)
        .order_by(TenderSourcePayload.created_at.desc())
        .limit(1)
    )
    if existing_payload:
        existing_intake = session.scalar(
            select(TenderIntakeRecord).where(TenderIntakeRecord.intake_id == existing_payload.intake_id)
        )
        if existing_intake:
            return existing_intake.deal_id, True

    if source_procurement_number:
        existing_deal = session.scalar(
            select(Deal)
            .where(Deal.procurement_number == source_procurement_number, Deal.is_deleted.is_(False))
            .order_by(Deal.created_at.desc())
            .limit(1)
        )
        if existing_deal:
            return existing_deal.deal_id, True

    return None, False


def _sync_deal_metadata_from_intake(session: Session, deal: Deal, payload: CreateTenderIntakeRequest) -> None:
    updated_fields: dict[str, str] = {}
    if not deal.procurement_number and payload.source_procurement_number:
        deal.procurement_number = payload.source_procurement_number
        updated_fields["procurement_number"] = payload.source_procurement_number
    if not deal.customer_name and payload.source_customer_name:
        deal.customer_name = payload.source_customer_name
        updated_fields["customer_name"] = payload.source_customer_name
    if not deal.procurement_channel and _map_procurement_channel(payload.source_type):
        deal.procurement_channel = _map_procurement_channel(payload.source_type)
        updated_fields["procurement_channel"] = str(deal.procurement_channel)
    if updated_fields:
        deal.updated_at = utcnow()
        session.add(deal)
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="deal_metadata_updated",
            source_module_id="M-001",
            severity=EventSeverity.INFO,
            payload_json=updated_fields,
        )


def _get_payload(session: Session, intake_id: str) -> TenderSourcePayload:
    payload = session.scalar(select(TenderSourcePayload).where(TenderSourcePayload.intake_id == intake_id))
    if not payload:
        raise NotFoundError(f"Source payload for intake '{intake_id}' was not found")
    return payload


def create_tender_intake(session: Session, payload: CreateTenderIntakeRequest) -> tuple[TenderIntakeRecord, TenderSourcePayload]:
    payload_hash = compute_payload_hash(payload.payload_json)
    existing_deal_id, duplicate_hint = _find_duplicate_deal_id(
        session,
        source_type=payload.source_type,
        source_procurement_number=payload.source_procurement_number,
        payload_hash=payload_hash,
    )
    deal = (
        session.scalar(select(Deal).where(Deal.deal_id == existing_deal_id, Deal.is_deleted.is_(False)))
        if existing_deal_id
        else None
    )
    if not deal:
        deal = _create_new_deal(session, payload)

    intake = TenderIntakeRecord(
        intake_id=next_intake_id(session, TenderIntakeRecord.intake_id),
        deal_id=deal.deal_id,
        source_type=payload.source_type,
        source_channel=require_non_empty(payload.source_channel, "source_channel"),
        source_title=require_non_empty(payload.source_title, "source_title"),
        source_customer_name=require_non_empty(payload.source_customer_name, "source_customer_name"),
        source_procurement_number=payload.source_procurement_number,
        intake_status=IntakeStatus.RECEIVED,
        duplicate_hint=duplicate_hint,
        received_at=utcnow(),
        normalized_at=utcnow(),
    )
    source_payload = TenderSourcePayload(
        intake_id=intake.intake_id,
        payload_json=payload.payload_json,
        payload_hash=payload_hash,
    )
    session.add(intake)
    session.flush()
    source_payload.intake_id = intake.intake_id
    session.add(source_payload)

    try:
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="tender_intake_received",
            source_module_id="M-008",
            severity=EventSeverity.INFO,
            payload_json={"intake_id": intake.intake_id, "source_type": str(payload.source_type)},
        )
        intake.intake_status = IntakeStatus.NORMALIZED
        intake.normalized_at = utcnow()
        intake.updated_at = utcnow()
        session.add(intake)
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="tender_intake_normalized",
            source_module_id="M-008",
            severity=EventSeverity.INFO,
            payload_json={"intake_id": intake.intake_id, "payload_hash": payload_hash},
        )
        _sync_deal_metadata_from_intake(session, deal, payload)
        _link_source_refs(session, deal, payload)
        intake.intake_status = IntakeStatus.LINKED
        intake.updated_at = utcnow()
        session.add(intake)
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="tender_intake_linked",
            source_module_id="M-008",
            severity=EventSeverity.INFO,
            payload_json={
                "intake_id": intake.intake_id,
                "deal_id": deal.deal_id,
                "duplicate_hint": duplicate_hint,
            },
        )
        session.commit()
    except Exception as exc:
        intake.intake_status = IntakeStatus.FAILED
        intake.updated_at = utcnow()
        session.add(intake)
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="tender_intake_failed",
            source_module_id="M-008",
            severity=EventSeverity.HIGH,
            payload_json={"intake_id": intake.intake_id, "error": str(exc)},
        )
        session.commit()
        raise

    session.refresh(intake)
    session.refresh(source_payload)
    return intake, source_payload


def get_tender_intake(session: Session, intake_id: str) -> tuple[TenderIntakeRecord, TenderSourcePayload]:
    intake = session.scalar(select(TenderIntakeRecord).where(TenderIntakeRecord.intake_id == intake_id))
    if not intake:
        raise NotFoundError(f"Tender intake '{intake_id}' was not found")
    return intake, _get_payload(session, intake_id)


def list_tender_intakes(session: Session, *, deal_id: str | None = None) -> list[tuple[TenderIntakeRecord, TenderSourcePayload]]:
    query = select(TenderIntakeRecord).order_by(TenderIntakeRecord.created_at.desc())
    if deal_id:
        query = query.where(TenderIntakeRecord.deal_id == deal_id)
    records = list(session.scalars(query))
    return [(record, _get_payload(session, record.intake_id)) for record in records]

