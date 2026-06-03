from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.execution_command.service import get_execution_command_set
from src.modules.incidents.models import EscalationRecord, IncidentRecord, IncidentSet
from src.modules.incidents.schemas import BuildIncidentSetRequest, EscalateIncidentRequest, RegisterIncidentRequest
from src.shared.db.base import utcnow
from src.shared.enums import EscalationStatus, EventSeverity, IncidentStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_escalation_id, next_incident_id, next_incident_set_id
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, incident_set_id: str) -> IncidentSet:
    record = session.scalar(select(IncidentSet).where(IncidentSet.incident_set_id == incident_set_id))
    if not record:
        raise NotFoundError(f"Incident set '{incident_set_id}' was not found")
    return record


def _get_record(session: Session, incident_id: str) -> IncidentRecord:
    record = session.scalar(select(IncidentRecord).where(IncidentRecord.incident_id == incident_id))
    if not record:
        raise NotFoundError(f"Incident record '{incident_id}' was not found")
    return record


def _get_records(session: Session, incident_set_id: str) -> list[IncidentRecord]:
    return list(
        session.scalars(
            select(IncidentRecord)
            .where(IncidentRecord.incident_set_id == incident_set_id)
            .order_by(IncidentRecord.created_at.asc(), IncidentRecord.id.asc())
        )
    )


def _get_escalations(session: Session, incident_id: str) -> list[EscalationRecord]:
    return list(
        session.scalars(
            select(EscalationRecord)
            .where(EscalationRecord.incident_id == incident_id)
            .order_by(EscalationRecord.created_at.asc(), EscalationRecord.id.asc())
        )
    )


def build_incident_set(session: Session, payload: BuildIncidentSetRequest) -> IncidentSet:
    execution_set, _bindings, _records = get_execution_command_set(session, payload.execution_command_set_id)
    require_same_reference(payload.deal_id, execution_set.deal_id, "deal_id")
    incident_set = IncidentSet(
        incident_set_id=next_incident_set_id(session, IncidentSet.incident_set_id),
        deal_id=payload.deal_id,
        execution_command_set_id=execution_set.execution_command_set_id,
        incident_status=IncidentStatus.OPEN,
    )
    session.add(incident_set)
    session.flush()
    try:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="incident_set_built",
            source_module_id="M-045",
            severity=EventSeverity.INFO,
            payload_json={
                "incident_set_id": incident_set.incident_set_id,
                "execution_command_set_id": execution_set.execution_command_set_id,
            },
        )
        session.commit()
    except Exception:
        session.rollback()
        raise
    session.refresh(incident_set)
    return incident_set


def register_incident(session: Session, payload: RegisterIncidentRequest) -> IncidentRecord:
    incident_set = _get_set(session, payload.incident_set_id)
    record = IncidentRecord(
        incident_id=next_incident_id(session, IncidentRecord.incident_id),
        incident_set_id=incident_set.incident_set_id,
        incident_type=payload.incident_type,
        severity=payload.severity,
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(record)
    incident_set.incident_status = IncidentStatus.OPEN
    incident_set.updated_at = utcnow()
    session.add(incident_set)
    append_event_record(
        session,
        deal_id=incident_set.deal_id,
        event_code="incident_recorded",
        source_module_id="M-045",
        severity=EventSeverity.INFO if str(payload.severity) in {"LOW", "MEDIUM"} else EventSeverity.HIGH,
        payload_json={
            "incident_set_id": incident_set.incident_set_id,
            "incident_id": record.incident_id,
            "incident_type": str(payload.incident_type),
            "severity": str(payload.severity),
        },
    )
    session.commit()
    session.refresh(record)
    return record


def escalate_incident(session: Session, payload: EscalateIncidentRequest) -> EscalationRecord:
    incident = _get_record(session, payload.incident_id)
    incident_set = _get_set(session, incident.incident_set_id)
    escalation = EscalationRecord(
        escalation_id=next_escalation_id(session, EscalationRecord.escalation_id),
        incident_id=incident.incident_id,
        escalation_level=payload.escalation_level,
        escalation_status=payload.escalation_status,
        notes=payload.notes,
    )
    session.add(escalation)
    if payload.incident_status:
        incident_set.incident_status = payload.incident_status
    elif payload.escalation_status == EscalationStatus.RESOLVED:
        incident_set.incident_status = IncidentStatus.CONTAINED
    incident_set.updated_at = utcnow()
    session.add(incident_set)
    append_event_record(
        session,
        deal_id=incident_set.deal_id,
        event_code="incident_escalated",
        source_module_id="M-045",
        severity=EventSeverity.INFO,
        payload_json={
            "incident_set_id": incident_set.incident_set_id,
            "incident_id": incident.incident_id,
            "escalation_id": escalation.escalation_id,
            "escalation_level": str(payload.escalation_level),
            "escalation_status": str(payload.escalation_status),
            "incident_status": str(incident_set.incident_status),
        },
    )
    if incident_set.incident_status == IncidentStatus.RESOLVED:
        append_event_record(
            session,
            deal_id=incident_set.deal_id,
            event_code="incident_resolved",
            source_module_id="M-045",
            severity=EventSeverity.INFO,
            payload_json={
                "incident_set_id": incident_set.incident_set_id,
                "incident_id": incident.incident_id,
                "escalation_id": escalation.escalation_id,
            },
        )
    session.commit()
    session.refresh(escalation)
    return escalation


def get_incident_set(
    session: Session,
    incident_set_id: str,
) -> tuple[IncidentSet, list[tuple[IncidentRecord, list[EscalationRecord]]]]:
    incident_set = _get_set(session, incident_set_id)
    records = _get_records(session, incident_set_id)
    return incident_set, [(record, _get_escalations(session, record.incident_id)) for record in records]


def list_incident_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[IncidentSet, list[tuple[IncidentRecord, list[EscalationRecord]]]]]:
    query = select(IncidentSet).order_by(IncidentSet.created_at.desc())
    if deal_id:
        query = query.where(IncidentSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_incident_set(session, item.incident_set_id) for item in sets]


def get_incident_record(
    session: Session,
    incident_id: str,
) -> tuple[IncidentRecord, list[EscalationRecord]]:
    record = _get_record(session, incident_id)
    return record, _get_escalations(session, incident_id)
