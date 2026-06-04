from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.incident_register.models import (
    IncidentRegisterEvent,
    IncidentRegisterFlag,
    IncidentRegisterRecord,
    IncidentRegisterSet,
)
from src.modules.incident_register.schemas import (
    BuildIncidentRegisterRequest,
    RegisterIncidentRegisterEventRequest,
)
from src.modules.logistics_tracking.models import LogisticsTrackingSet
from src.shared.db.base import utcnow
from src.shared.delivery_recovery_package import load_delivery_helper_context
from src.shared.enums import (
    EventSeverity,
    IncidentRegisterEventType,
    IncidentRegisterStatus,
    IncidentRegisterType,
    LogisticsStatus,
    RiskSeverity,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_incident_register_event_id,
    next_incident_register_id,
    next_incident_register_set_id,
)
from src.shared.validation import require_non_empty


def _get_set(session: Session, incident_register_set_id: str) -> IncidentRegisterSet:
    record = session.scalar(
        select(IncidentRegisterSet).where(
            IncidentRegisterSet.incident_register_set_id == incident_register_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Incident register set '{incident_register_set_id}' was not found")
    return record


def _get_record(session: Session, incident_register_id: str) -> IncidentRegisterRecord:
    record = session.scalar(
        select(IncidentRegisterRecord).where(IncidentRegisterRecord.incident_register_id == incident_register_id)
    )
    if not record:
        raise NotFoundError(f"Incident register record '{incident_register_id}' was not found")
    return record


def _get_records(session: Session, incident_register_set_id: str) -> list[IncidentRegisterRecord]:
    return list(
        session.scalars(
            select(IncidentRegisterRecord)
            .where(IncidentRegisterRecord.incident_register_set_id == incident_register_set_id)
            .order_by(IncidentRegisterRecord.created_at.asc(), IncidentRegisterRecord.id.asc())
        )
    )


def _get_events(session: Session, incident_register_id: str) -> list[IncidentRegisterEvent]:
    return list(
        session.scalars(
            select(IncidentRegisterEvent)
            .where(IncidentRegisterEvent.incident_register_id == incident_register_id)
            .order_by(IncidentRegisterEvent.event_timestamp.asc(), IncidentRegisterEvent.id.asc())
        )
    )


def _get_flags(session: Session, incident_register_id: str) -> list[IncidentRegisterFlag]:
    return list(
        session.scalars(
            select(IncidentRegisterFlag)
            .where(IncidentRegisterFlag.incident_register_id == incident_register_id)
            .order_by(IncidentRegisterFlag.created_at.asc(), IncidentRegisterFlag.id.asc())
        )
    )


def _latest_logistics_set(session: Session, deal_id: str) -> LogisticsTrackingSet | None:
    return session.scalar(
        select(LogisticsTrackingSet)
        .where(LogisticsTrackingSet.deal_id == deal_id)
        .order_by(LogisticsTrackingSet.created_at.desc(), LogisticsTrackingSet.id.desc())
    )


def build_incident_register(session: Session, payload: BuildIncidentRegisterRequest) -> IncidentRegisterSet:
    logistics_set = _latest_logistics_set(session, payload.deal_id)
    if not logistics_set:
        raise ValidationError("Incident register requires canonical logistics tracking")

    helper_context = load_delivery_helper_context(session, payload.deal_id)
    incident_status = IncidentRegisterStatus.MONITORING
    incident_type = IncidentRegisterType.OTHER
    severity = RiskSeverity.LOW
    summary_text = "No active incident detected; delivery and acceptance are under monitoring."

    if logistics_set.logistics_status in {LogisticsStatus.DELAYED, LogisticsStatus.FAILED}:
        incident_status = IncidentRegisterStatus.OPEN
        incident_type = IncidentRegisterType.LOGISTICS
        severity = RiskSeverity.HIGH
        summary_text = "Logistics deviation detected from canonical delivery context."
    elif helper_context.payment_record and float(helper_context.payment_record.collected_amount) < float(
        helper_context.payment_record.expected_amount
    ):
        incident_status = IncidentRegisterStatus.OPEN
        incident_type = IncidentRegisterType.PAYMENT
        severity = RiskSeverity.MEDIUM
        summary_text = "Payment collection context shows unresolved receivables."

    register_set = IncidentRegisterSet(
        incident_register_set_id=next_incident_register_set_id(
            session, IncidentRegisterSet.incident_register_set_id
        ),
        deal_id=payload.deal_id,
        incident_status=incident_status,
    )
    session.add(register_set)
    session.flush()
    try:
        record = IncidentRegisterRecord(
            incident_register_id=next_incident_register_id(
                session, IncidentRegisterRecord.incident_register_id
            ),
            incident_register_set_id=register_set.incident_register_set_id,
            incident_type=incident_type,
            severity=severity,
            summary_text=summary_text,
        )
        session.add(record)
        session.flush()
        session.add(
            IncidentRegisterEvent(
                incident_register_event_id=next_incident_register_event_id(
                    session, IncidentRegisterEvent.incident_register_event_id
                ),
                incident_register_id=record.incident_register_id,
                event_type=IncidentRegisterEventType.REGISTERED,
                event_timestamp=utcnow(),
                summary=summary_text,
                source_ref=logistics_set.logistics_tracking_set_id,
            )
        )
        if incident_status == IncidentRegisterStatus.OPEN:
            session.add(
                IncidentRegisterFlag(
                    incident_register_id=record.incident_register_id,
                    flag_code="OPEN_INCIDENT",
                    severity=severity,
                    summary=summary_text,
                )
            )
        register_set.updated_at = utcnow()
        session.add(register_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="incident_register_built",
            source_module_id="M-040",
            severity=EventSeverity.INFO,
            payload_json={
                "incident_register_set_id": register_set.incident_register_set_id,
                "incident_register_id": record.incident_register_id,
            },
        )
        session.commit()
    except Exception as exc:
        register_set.incident_status = IncidentRegisterStatus.FAILED
        register_set.updated_at = utcnow()
        session.add(register_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="incident_register_failed",
            source_module_id="M-040",
            severity=EventSeverity.HIGH,
            payload_json={"incident_register_set_id": register_set.incident_register_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(register_set)
    return register_set


def register_incident_register_event(
    session: Session,
    payload: RegisterIncidentRegisterEventRequest,
) -> IncidentRegisterEvent:
    record = _get_record(session, payload.incident_register_id)
    register_set = _get_set(session, record.incident_register_set_id)
    event = IncidentRegisterEvent(
        incident_register_event_id=next_incident_register_event_id(
            session, IncidentRegisterEvent.incident_register_event_id
        ),
        incident_register_id=record.incident_register_id,
        event_type=payload.event_type,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.severity:
        record.severity = payload.severity
    if payload.incident_status:
        register_set.incident_status = payload.incident_status
    elif payload.event_type == IncidentRegisterEventType.ESCALATED:
        register_set.incident_status = IncidentRegisterStatus.ESCALATED
    elif payload.event_type == IncidentRegisterEventType.RESOLVED:
        register_set.incident_status = IncidentRegisterStatus.RESOLVED
    else:
        register_set.incident_status = IncidentRegisterStatus.OPEN
    record.summary_text = require_non_empty(payload.summary, "summary")
    record.updated_at = utcnow()
    register_set.updated_at = utcnow()
    if payload.flag_code or payload.event_type == IncidentRegisterEventType.ESCALATED:
        session.add(
            IncidentRegisterFlag(
                incident_register_id=record.incident_register_id,
                flag_code=payload.flag_code or "ESCALATED_INCIDENT",
                severity=payload.severity or RiskSeverity.HIGH,
                summary=event.summary,
            )
        )
    session.add(record)
    session.add(register_set)
    append_event_record(
        session,
        deal_id=register_set.deal_id,
        event_code="incident_register_event_recorded",
        source_module_id="M-040",
        severity=EventSeverity.INFO,
        payload_json={
            "incident_register_set_id": register_set.incident_register_set_id,
            "incident_register_id": record.incident_register_id,
            "event_type": str(payload.event_type),
            "incident_status": str(register_set.incident_status),
        },
    )
    session.commit()
    session.refresh(event)
    return event


def get_incident_register_set(
    session: Session,
    incident_register_set_id: str,
) -> tuple[IncidentRegisterSet, list[tuple[IncidentRegisterRecord, list[IncidentRegisterEvent], list[IncidentRegisterFlag]]]]:
    register_set = _get_set(session, incident_register_set_id)
    records = _get_records(session, incident_register_set_id)
    return register_set, [
        (record, _get_events(session, record.incident_register_id), _get_flags(session, record.incident_register_id))
        for record in records
    ]


def list_incident_register_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[IncidentRegisterSet, list[tuple[IncidentRegisterRecord, list[IncidentRegisterEvent], list[IncidentRegisterFlag]]]]]:
    query = select(IncidentRegisterSet).order_by(
        IncidentRegisterSet.created_at.desc(), IncidentRegisterSet.id.desc()
    )
    if deal_id:
        query = query.where(IncidentRegisterSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_incident_register_set(session, item.incident_register_set_id) for item in sets]


def get_incident_register_record(
    session: Session,
    incident_register_id: str,
) -> tuple[IncidentRegisterRecord, list[IncidentRegisterEvent], list[IncidentRegisterFlag]]:
    record = _get_record(session, incident_register_id)
    return record, _get_events(session, incident_register_id), _get_flags(session, incident_register_id)
