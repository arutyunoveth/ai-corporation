from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from src.modules.deal_registry.models import Deal
from src.modules.event_log.models import DecisionRecord, EventRecord
from src.modules.event_log.schemas import AppendDecisionRequest, AppendEventRequest
from src.shared.events import DECISION_CODES
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_decision_id, next_event_id
from src.shared.validation import require_non_empty


def append_event_record(
    session: Session,
    *,
    deal_id: str | None,
    event_code: str,
    source_module_id: str | None,
    severity: str,
    payload_json: dict | None = None,
    source_agent_code: str | None = None,
) -> EventRecord:
    if deal_id:
        deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id, Deal.is_deleted.is_(False)))
        if not deal:
            raise NotFoundError(f"Deal '{deal_id}' was not found")
    if not any([deal_id, source_module_id, source_agent_code]):
        raise ValidationError("At least one of deal_id, source_module_id, source_agent_code must be provided")
    event = EventRecord(
        event_id=next_event_id(session, EventRecord.event_id),
        deal_id=deal_id,
        event_code=require_non_empty(event_code, "event_code"),
        source_module_id=source_module_id,
        source_agent_code=source_agent_code,
        severity=str(severity),
        payload_json=payload_json,
    )
    session.add(event)
    session.flush()
    return event


def append_event(session: Session, payload: AppendEventRequest) -> EventRecord:
    event = append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code=payload.event_code,
        source_module_id=payload.source_module_id,
        source_agent_code=payload.source_agent_code,
        severity=payload.severity,
        payload_json=payload.payload_json,
    )
    session.commit()
    session.refresh(event)
    return event


def append_decision(session: Session, payload: AppendDecisionRequest) -> DecisionRecord:
    require_non_empty(payload.deal_id, "deal_id")
    require_non_empty(payload.decision_code, "decision_code")
    if not payload.rationale and not payload.payload_json:
        raise ValidationError("Decision must include rationale or payload_json")
    deal = session.scalar(select(Deal).where(Deal.deal_id == payload.deal_id, Deal.is_deleted.is_(False)))
    if not deal:
        raise NotFoundError(f"Deal '{payload.deal_id}' was not found")
    decision = DecisionRecord(
        decision_id=next_decision_id(session, DecisionRecord.decision_id),
        deal_id=payload.deal_id,
        decision_code=payload.decision_code,
        decided_by_type=payload.decided_by_type,
        decided_by_ref=payload.decided_by_ref,
        rationale=payload.rationale,
        payload_json=payload.payload_json,
    )
    session.add(decision)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="decision_recorded",
        source_module_id="M-004",
        severity="INFO",
        payload_json={
            "decision_id": decision.decision_id,
            "decision_code": decision.decision_code,
            "is_known_decision_code": payload.decision_code in DECISION_CODES,
        },
    )
    session.commit()
    session.refresh(decision)
    return decision


def list_events(session: Session, *, deal_id: str | None = None) -> list[EventRecord]:
    query: Select[tuple[EventRecord]] = select(EventRecord).order_by(EventRecord.created_at.asc(), EventRecord.id.asc())
    if deal_id:
        query = query.where(EventRecord.deal_id == deal_id)
    return list(session.scalars(query))


def list_decisions(session: Session, *, deal_id: str | None = None) -> list[DecisionRecord]:
    query: Select[tuple[DecisionRecord]] = select(DecisionRecord).order_by(
        DecisionRecord.created_at.asc(),
        DecisionRecord.id.asc(),
    )
    if deal_id:
        query = query.where(DecisionRecord.deal_id == deal_id)
    return list(session.scalars(query))
