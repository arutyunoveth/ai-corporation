from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.delivery_milestones.models import (
    DeliveryMilestoneEvent,
    DeliveryMilestoneRecord,
    DeliveryMilestoneSet,
)
from src.modules.delivery_milestones.schemas import BuildDeliveryMilestonesRequest, RegisterDeliveryMilestoneEventRequest
from src.modules.event_log.service import append_event_record
from src.modules.execution_command.service import advance_execution_command, get_execution_command_set
from src.shared.db.base import utcnow
from src.shared.enums import (
    DeliveryMilestoneStatus,
    EventSeverity,
    ExecutionCommandStatus,
    ExecutionPhase,
    MilestoneState,
)
from src.shared.errors import NotFoundError
from src.shared.ids import (
    next_delivery_milestone_event_id,
    next_delivery_milestone_id,
    next_delivery_milestone_set_id,
)
from src.shared.validation import require_non_empty, require_same_reference

_DEFAULT_MILESTONES = [
    ("MS-LAUNCH", "Execution Launch", 0, MilestoneState.DONE),
    ("MS-PROCUREMENT", "Supplier Procurement", 7, MilestoneState.PLANNED),
    ("MS-SHIPPING", "Shipping Window", 14, MilestoneState.PLANNED),
    ("MS-ACCEPTANCE", "Acceptance Sign-Off", 21, MilestoneState.PLANNED),
    ("MS-COLLECTION", "Payment Collection", 35, MilestoneState.PLANNED),
]


def _get_set(session: Session, delivery_milestone_set_id: str) -> DeliveryMilestoneSet:
    record = session.scalar(
        select(DeliveryMilestoneSet).where(DeliveryMilestoneSet.delivery_milestone_set_id == delivery_milestone_set_id)
    )
    if not record:
        raise NotFoundError(f"Delivery milestone set '{delivery_milestone_set_id}' was not found")
    return record


def _get_record(session: Session, delivery_milestone_id: str) -> DeliveryMilestoneRecord:
    record = session.scalar(
        select(DeliveryMilestoneRecord).where(DeliveryMilestoneRecord.delivery_milestone_id == delivery_milestone_id)
    )
    if not record:
        raise NotFoundError(f"Delivery milestone record '{delivery_milestone_id}' was not found")
    return record


def _get_records(session: Session, delivery_milestone_set_id: str) -> list[DeliveryMilestoneRecord]:
    return list(
        session.scalars(
            select(DeliveryMilestoneRecord)
            .where(DeliveryMilestoneRecord.delivery_milestone_set_id == delivery_milestone_set_id)
            .order_by(DeliveryMilestoneRecord.created_at.asc(), DeliveryMilestoneRecord.id.asc())
        )
    )


def _get_events(session: Session, delivery_milestone_id: str) -> list[DeliveryMilestoneEvent]:
    return list(
        session.scalars(
            select(DeliveryMilestoneEvent)
            .where(DeliveryMilestoneEvent.delivery_milestone_id == delivery_milestone_id)
            .order_by(DeliveryMilestoneEvent.event_timestamp.asc(), DeliveryMilestoneEvent.id.asc())
        )
    )


def _recompute_status(records: list[DeliveryMilestoneRecord]) -> DeliveryMilestoneStatus:
    states = {str(record.milestone_state) for record in records}
    if states and states <= {str(MilestoneState.DONE)}:
        return DeliveryMilestoneStatus.COMPLETED
    if any(state in {str(MilestoneState.DELAYED), str(MilestoneState.CANCELLED)} for state in states):
        return DeliveryMilestoneStatus.BLOCKED
    return DeliveryMilestoneStatus.ACTIVE


def _phase_for_milestone(record: DeliveryMilestoneRecord) -> ExecutionPhase | None:
    if record.milestone_code == "MS-PROCUREMENT":
        return ExecutionPhase.PROCUREMENT
    if record.milestone_code == "MS-SHIPPING":
        return ExecutionPhase.SHIPPING
    if record.milestone_code == "MS-ACCEPTANCE":
        return ExecutionPhase.ACCEPTANCE
    if record.milestone_code == "MS-COLLECTION":
        return ExecutionPhase.COLLECTION
    return ExecutionPhase.LAUNCHED if record.milestone_code == "MS-LAUNCH" else None


def build_delivery_milestones(session: Session, payload: BuildDeliveryMilestonesRequest) -> DeliveryMilestoneSet:
    execution_set, _bindings, _records = get_execution_command_set(session, payload.execution_command_set_id)
    require_same_reference(payload.deal_id, execution_set.deal_id, "deal_id")

    milestone_set = DeliveryMilestoneSet(
        delivery_milestone_set_id=next_delivery_milestone_set_id(session, DeliveryMilestoneSet.delivery_milestone_set_id),
        deal_id=payload.deal_id,
        execution_command_set_id=execution_set.execution_command_set_id,
        milestone_status=DeliveryMilestoneStatus.ACTIVE,
    )
    session.add(milestone_set)
    session.flush()
    try:
        seeds = payload.milestones
        if not seeds:
            now = utcnow()
            seeds = [
                {
                    "milestone_code": code,
                    "milestone_name": name,
                    "due_date": now + timedelta(days=offset) if offset else now,
                    "milestone_state": state,
                }
                for code, name, offset, state in _DEFAULT_MILESTONES
            ]
        for seed in seeds:
            session.add(
                DeliveryMilestoneRecord(
                    delivery_milestone_id=next_delivery_milestone_id(session, DeliveryMilestoneRecord.delivery_milestone_id),
                    delivery_milestone_set_id=milestone_set.delivery_milestone_set_id,
                    milestone_code=seed["milestone_code"] if isinstance(seed, dict) else seed.milestone_code,
                    milestone_name=seed["milestone_name"] if isinstance(seed, dict) else seed.milestone_name,
                    due_date=seed["due_date"] if isinstance(seed, dict) else seed.due_date,
                    milestone_state=seed["milestone_state"] if isinstance(seed, dict) else seed.milestone_state,
                )
            )
            session.flush()
        milestone_set.updated_at = utcnow()
        session.add(milestone_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="delivery_milestones_built",
            source_module_id="M-041",
            severity=EventSeverity.INFO,
            payload_json={
                "delivery_milestone_set_id": milestone_set.delivery_milestone_set_id,
                "execution_command_set_id": execution_set.execution_command_set_id,
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="delivery_milestones_failed",
            source_module_id="M-041",
            severity=EventSeverity.HIGH,
            payload_json={"delivery_milestone_set_id": milestone_set.delivery_milestone_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(milestone_set)
    return milestone_set


def register_delivery_milestone_event(session: Session, payload: RegisterDeliveryMilestoneEventRequest) -> DeliveryMilestoneEvent:
    record = _get_record(session, payload.delivery_milestone_id)
    milestone_set = _get_set(session, record.delivery_milestone_set_id)
    event = DeliveryMilestoneEvent(
        delivery_milestone_event_id=next_delivery_milestone_event_id(
            session, DeliveryMilestoneEvent.delivery_milestone_event_id
        ),
        delivery_milestone_id=record.delivery_milestone_id,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.milestone_state:
        record.milestone_state = payload.milestone_state
    record.updated_at = utcnow()
    records = _get_records(session, milestone_set.delivery_milestone_set_id)
    updated_records = [item if item.delivery_milestone_id != record.delivery_milestone_id else record for item in records]
    milestone_set.milestone_status = _recompute_status(updated_records)
    milestone_set.updated_at = utcnow()
    session.add(record)
    session.add(milestone_set)
    append_event_record(
        session,
        deal_id=milestone_set.deal_id,
        event_code="delivery_milestone_event_recorded",
        source_module_id="M-041",
        severity=EventSeverity.INFO,
        payload_json={
            "delivery_milestone_set_id": milestone_set.delivery_milestone_set_id,
            "delivery_milestone_id": record.delivery_milestone_id,
            "milestone_state": str(record.milestone_state),
        },
    )
    if payload.milestone_state == MilestoneState.DONE:
        phase = _phase_for_milestone(record)
        if phase:
            advance_execution_command(
                session,
                execution_command_set_id=milestone_set.execution_command_set_id,
                phase=phase,
                summary_text=event.summary,
                source_module_id="M-041",
                status=ExecutionCommandStatus.IN_PROGRESS,
            )
    session.commit()
    session.refresh(event)
    return event


def get_delivery_milestone_set(
    session: Session,
    delivery_milestone_set_id: str,
) -> tuple[DeliveryMilestoneSet, list[tuple[DeliveryMilestoneRecord, list[DeliveryMilestoneEvent]]]]:
    milestone_set = _get_set(session, delivery_milestone_set_id)
    records = _get_records(session, delivery_milestone_set_id)
    return milestone_set, [(record, _get_events(session, record.delivery_milestone_id)) for record in records]


def list_delivery_milestone_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[DeliveryMilestoneSet, list[tuple[DeliveryMilestoneRecord, list[DeliveryMilestoneEvent]]]]]:
    query = select(DeliveryMilestoneSet).order_by(DeliveryMilestoneSet.created_at.desc())
    if deal_id:
        query = query.where(DeliveryMilestoneSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_delivery_milestone_set(session, item.delivery_milestone_set_id) for item in sets]


def get_delivery_milestone_record(
    session: Session,
    delivery_milestone_id: str,
) -> tuple[DeliveryMilestoneRecord, list[DeliveryMilestoneEvent]]:
    record = _get_record(session, delivery_milestone_id)
    return record, _get_events(session, delivery_milestone_id)
