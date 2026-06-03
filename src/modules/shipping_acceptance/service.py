from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.execution_command.service import advance_execution_command, get_execution_command_set
from src.modules.shipping_acceptance.models import (
    ShippingAcceptanceEvent,
    ShippingAcceptanceRecord,
    ShippingAcceptanceSet,
)
from src.modules.shipping_acceptance.schemas import (
    BuildShippingAcceptanceRequest,
    RegisterShippingAcceptanceEventRequest,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    ExecutionCommandStatus,
    ExecutionPhase,
    ShippingAcceptanceState,
    ShippingAcceptanceStatus,
)
from src.shared.errors import NotFoundError
from src.shared.ids import (
    next_shipping_acceptance_event_id,
    next_shipping_acceptance_id,
    next_shipping_acceptance_set_id,
)
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, shipping_acceptance_set_id: str) -> ShippingAcceptanceSet:
    record = session.scalar(
        select(ShippingAcceptanceSet).where(
            ShippingAcceptanceSet.shipping_acceptance_set_id == shipping_acceptance_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Shipping acceptance set '{shipping_acceptance_set_id}' was not found")
    return record


def _get_record(session: Session, shipping_acceptance_id: str) -> ShippingAcceptanceRecord:
    record = session.scalar(
        select(ShippingAcceptanceRecord).where(ShippingAcceptanceRecord.shipping_acceptance_id == shipping_acceptance_id)
    )
    if not record:
        raise NotFoundError(f"Shipping acceptance record '{shipping_acceptance_id}' was not found")
    return record


def _get_records(session: Session, shipping_acceptance_set_id: str) -> list[ShippingAcceptanceRecord]:
    return list(
        session.scalars(
            select(ShippingAcceptanceRecord)
            .where(ShippingAcceptanceRecord.shipping_acceptance_set_id == shipping_acceptance_set_id)
            .order_by(ShippingAcceptanceRecord.created_at.asc(), ShippingAcceptanceRecord.id.asc())
        )
    )


def _get_events(session: Session, shipping_acceptance_id: str) -> list[ShippingAcceptanceEvent]:
    return list(
        session.scalars(
            select(ShippingAcceptanceEvent)
            .where(ShippingAcceptanceEvent.shipping_acceptance_id == shipping_acceptance_id)
            .order_by(ShippingAcceptanceEvent.event_timestamp.asc(), ShippingAcceptanceEvent.id.asc())
        )
    )


def build_shipping_acceptance(session: Session, payload: BuildShippingAcceptanceRequest) -> ShippingAcceptanceSet:
    execution_set, _bindings, _records = get_execution_command_set(session, payload.execution_command_set_id)
    require_same_reference(payload.deal_id, execution_set.deal_id, "deal_id")
    shipping_set = ShippingAcceptanceSet(
        shipping_acceptance_set_id=next_shipping_acceptance_set_id(
            session, ShippingAcceptanceSet.shipping_acceptance_set_id
        ),
        deal_id=payload.deal_id,
        execution_command_set_id=execution_set.execution_command_set_id,
        shipping_status=ShippingAcceptanceStatus.ACTIVE,
    )
    session.add(shipping_set)
    session.flush()
    try:
        session.add(
            ShippingAcceptanceRecord(
                shipping_acceptance_id=next_shipping_acceptance_id(
                    session, ShippingAcceptanceRecord.shipping_acceptance_id
                ),
                shipping_acceptance_set_id=shipping_set.shipping_acceptance_set_id,
                shipment_ref=payload.shipment_ref,
                acceptance_ref=payload.acceptance_ref,
                current_state=ShippingAcceptanceState.PLANNED,
            )
        )
        shipping_set.updated_at = utcnow()
        session.add(shipping_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="shipping_acceptance_built",
            source_module_id="M-043",
            severity=EventSeverity.INFO,
            payload_json={
                "shipping_acceptance_set_id": shipping_set.shipping_acceptance_set_id,
                "execution_command_set_id": execution_set.execution_command_set_id,
            },
        )
        session.commit()
    except Exception as exc:
        shipping_set.shipping_status = ShippingAcceptanceStatus.FAILED
        shipping_set.updated_at = utcnow()
        session.add(shipping_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="shipping_acceptance_failed",
            source_module_id="M-043",
            severity=EventSeverity.HIGH,
            payload_json={"shipping_acceptance_set_id": shipping_set.shipping_acceptance_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(shipping_set)
    return shipping_set


def register_shipping_acceptance_event(
    session: Session,
    payload: RegisterShippingAcceptanceEventRequest,
) -> ShippingAcceptanceEvent:
    record = _get_record(session, payload.shipping_acceptance_id)
    shipping_set = _get_set(session, record.shipping_acceptance_set_id)
    event = ShippingAcceptanceEvent(
        shipping_acceptance_event_id=next_shipping_acceptance_event_id(
            session, ShippingAcceptanceEvent.shipping_acceptance_event_id
        ),
        shipping_acceptance_id=record.shipping_acceptance_id,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.current_state:
        record.current_state = payload.current_state
    if payload.shipment_ref:
        record.shipment_ref = payload.shipment_ref
    if payload.acceptance_ref:
        record.acceptance_ref = payload.acceptance_ref
    record.updated_at = utcnow()

    if record.current_state == ShippingAcceptanceState.ACCEPTED:
        shipping_set.shipping_status = ShippingAcceptanceStatus.ACCEPTED
        phase = ExecutionPhase.ACCEPTANCE
    elif record.current_state == ShippingAcceptanceState.DELIVERED:
        shipping_set.shipping_status = ShippingAcceptanceStatus.DELIVERED
        phase = ExecutionPhase.SHIPPING
    elif record.current_state == ShippingAcceptanceState.REJECTED:
        shipping_set.shipping_status = ShippingAcceptanceStatus.FAILED
        phase = ExecutionPhase.ACCEPTANCE
    else:
        shipping_set.shipping_status = ShippingAcceptanceStatus.ACTIVE
        phase = ExecutionPhase.SHIPPING

    shipping_set.updated_at = utcnow()
    session.add(record)
    session.add(shipping_set)
    append_event_record(
        session,
        deal_id=shipping_set.deal_id,
        event_code="shipping_acceptance_event_recorded",
        source_module_id="M-043",
        severity=EventSeverity.INFO,
        payload_json={
            "shipping_acceptance_set_id": shipping_set.shipping_acceptance_set_id,
            "shipping_acceptance_id": record.shipping_acceptance_id,
            "current_state": str(record.current_state),
        },
    )
    advance_execution_command(
        session,
        execution_command_set_id=shipping_set.execution_command_set_id,
        phase=phase,
        summary_text=event.summary,
        source_module_id="M-043",
        status=ExecutionCommandStatus.ON_HOLD if shipping_set.shipping_status == ShippingAcceptanceStatus.FAILED else ExecutionCommandStatus.IN_PROGRESS,
    )
    session.commit()
    session.refresh(event)
    return event


def get_shipping_acceptance_set(
    session: Session,
    shipping_acceptance_set_id: str,
) -> tuple[ShippingAcceptanceSet, list[tuple[ShippingAcceptanceRecord, list[ShippingAcceptanceEvent]]]]:
    shipping_set = _get_set(session, shipping_acceptance_set_id)
    records = _get_records(session, shipping_acceptance_set_id)
    return shipping_set, [(record, _get_events(session, record.shipping_acceptance_id)) for record in records]


def list_shipping_acceptance_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ShippingAcceptanceSet, list[tuple[ShippingAcceptanceRecord, list[ShippingAcceptanceEvent]]]]]:
    query = select(ShippingAcceptanceSet).order_by(ShippingAcceptanceSet.created_at.desc())
    if deal_id:
        query = query.where(ShippingAcceptanceSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_shipping_acceptance_set(session, item.shipping_acceptance_set_id) for item in sets]


def get_shipping_acceptance_record(
    session: Session,
    shipping_acceptance_id: str,
) -> tuple[ShippingAcceptanceRecord, list[ShippingAcceptanceEvent]]:
    record = _get_record(session, shipping_acceptance_id)
    return record, _get_events(session, shipping_acceptance_id)
