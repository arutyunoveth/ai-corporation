from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.delivery_launch.models import DeliveryLaunchSet
from src.modules.event_log.service import append_event_record
from src.modules.execution_command.service import advance_execution_command, get_execution_command_set
from src.modules.supplier_fulfillment.models import (
    SupplierFulfillmentEvent,
    SupplierFulfillmentRecord,
    SupplierFulfillmentSet,
)
from src.modules.supplier_fulfillment.schemas import (
    BuildSupplierFulfillmentRequest,
    RegisterSupplierFulfillmentEventRequest,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    ExecutionCommandStatus,
    ExecutionPhase,
    SupplierFulfillmentState,
    SupplierFulfillmentStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.execution_package import load_execution_package
from src.shared.ids import (
    next_supplier_fulfillment_event_id,
    next_supplier_fulfillment_id,
    next_supplier_fulfillment_set_id,
)
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, supplier_fulfillment_set_id: str) -> SupplierFulfillmentSet:
    record = session.scalar(
        select(SupplierFulfillmentSet).where(
            SupplierFulfillmentSet.supplier_fulfillment_set_id == supplier_fulfillment_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Supplier fulfillment set '{supplier_fulfillment_set_id}' was not found")
    return record


def _get_record(session: Session, supplier_fulfillment_id: str) -> SupplierFulfillmentRecord:
    record = session.scalar(
        select(SupplierFulfillmentRecord).where(
            SupplierFulfillmentRecord.supplier_fulfillment_id == supplier_fulfillment_id
        )
    )
    if not record:
        raise NotFoundError(f"Supplier fulfillment record '{supplier_fulfillment_id}' was not found")
    return record


def _get_records(session: Session, supplier_fulfillment_set_id: str) -> list[SupplierFulfillmentRecord]:
    return list(
        session.scalars(
            select(SupplierFulfillmentRecord)
            .where(SupplierFulfillmentRecord.supplier_fulfillment_set_id == supplier_fulfillment_set_id)
            .order_by(SupplierFulfillmentRecord.created_at.asc(), SupplierFulfillmentRecord.id.asc())
        )
    )


def _get_events(session: Session, supplier_fulfillment_id: str) -> list[SupplierFulfillmentEvent]:
    return list(
        session.scalars(
            select(SupplierFulfillmentEvent)
            .where(SupplierFulfillmentEvent.supplier_fulfillment_id == supplier_fulfillment_id)
            .order_by(SupplierFulfillmentEvent.event_timestamp.asc(), SupplierFulfillmentEvent.id.asc())
        )
    )


def build_supplier_fulfillment(session: Session, payload: BuildSupplierFulfillmentRequest) -> SupplierFulfillmentSet:
    execution_set, _bindings, _records = get_execution_command_set(session, payload.execution_command_set_id)
    require_same_reference(payload.deal_id, execution_set.deal_id, "deal_id")
    launch_set = session.scalar(
        select(DeliveryLaunchSet).where(DeliveryLaunchSet.delivery_launch_set_id == execution_set.delivery_launch_set_id)
    )
    if not launch_set:
        raise NotFoundError(f"Delivery launch set '{execution_set.delivery_launch_set_id}' was not found")
    package = load_execution_package(
        session,
        deal_id=payload.deal_id,
        outcome_intake_set_id=launch_set.outcome_intake_set_id,
    )
    if not package.quote_recommendation or not package.recommended_quote:
        raise ValidationError("Supplier fulfillment requires a persisted winning quote recommendation")

    fulfillment_set = SupplierFulfillmentSet(
        supplier_fulfillment_set_id=next_supplier_fulfillment_set_id(
            session, SupplierFulfillmentSet.supplier_fulfillment_set_id
        ),
        deal_id=payload.deal_id,
        execution_command_set_id=execution_set.execution_command_set_id,
        fulfillment_status=SupplierFulfillmentStatus.ACTIVE,
    )
    session.add(fulfillment_set)
    session.flush()
    try:
        session.add(
            SupplierFulfillmentRecord(
                supplier_fulfillment_id=next_supplier_fulfillment_id(
                    session, SupplierFulfillmentRecord.supplier_fulfillment_id
                ),
                supplier_fulfillment_set_id=fulfillment_set.supplier_fulfillment_set_id,
                supplier_id=package.quote_recommendation.recommended_supplier_id,
                fulfillment_state=SupplierFulfillmentState.PENDING,
                summary_text="Awarded supplier fulfillment context opened from winning quote recommendation.",
            )
        )
        fulfillment_set.updated_at = utcnow()
        session.add(fulfillment_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_fulfillment_built",
            source_module_id="M-042",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_fulfillment_set_id": fulfillment_set.supplier_fulfillment_set_id,
                "execution_command_set_id": execution_set.execution_command_set_id,
                "supplier_id": package.quote_recommendation.recommended_supplier_id,
            },
        )
        session.commit()
    except Exception as exc:
        fulfillment_set.fulfillment_status = SupplierFulfillmentStatus.FAILED
        fulfillment_set.updated_at = utcnow()
        session.add(fulfillment_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_fulfillment_failed",
            source_module_id="M-042",
            severity=EventSeverity.HIGH,
            payload_json={"supplier_fulfillment_set_id": fulfillment_set.supplier_fulfillment_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(fulfillment_set)
    return fulfillment_set


def register_supplier_fulfillment_event(
    session: Session,
    payload: RegisterSupplierFulfillmentEventRequest,
) -> SupplierFulfillmentEvent:
    record = _get_record(session, payload.supplier_fulfillment_id)
    fulfillment_set = _get_set(session, record.supplier_fulfillment_set_id)
    event = SupplierFulfillmentEvent(
        supplier_fulfillment_event_id=next_supplier_fulfillment_event_id(
            session, SupplierFulfillmentEvent.supplier_fulfillment_event_id
        ),
        supplier_fulfillment_id=record.supplier_fulfillment_id,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.fulfillment_state:
        record.fulfillment_state = payload.fulfillment_state
    record.summary_text = event.summary
    record.updated_at = utcnow()
    if record.fulfillment_state == SupplierFulfillmentState.FULFILLED:
        fulfillment_set.fulfillment_status = SupplierFulfillmentStatus.COMPLETED
        phase = ExecutionPhase.SHIPPING
    elif record.fulfillment_state == SupplierFulfillmentState.DELAYED:
        fulfillment_set.fulfillment_status = SupplierFulfillmentStatus.AT_RISK
        phase = ExecutionPhase.PROCUREMENT
    elif record.fulfillment_state == SupplierFulfillmentState.FAILED:
        fulfillment_set.fulfillment_status = SupplierFulfillmentStatus.FAILED
        phase = ExecutionPhase.PROCUREMENT
    else:
        fulfillment_set.fulfillment_status = SupplierFulfillmentStatus.ACTIVE
        phase = ExecutionPhase.PROCUREMENT
    fulfillment_set.updated_at = utcnow()
    session.add(record)
    session.add(fulfillment_set)
    append_event_record(
        session,
        deal_id=fulfillment_set.deal_id,
        event_code="supplier_fulfillment_event_recorded",
        source_module_id="M-042",
        severity=EventSeverity.INFO,
        payload_json={
            "supplier_fulfillment_set_id": fulfillment_set.supplier_fulfillment_set_id,
            "supplier_fulfillment_id": record.supplier_fulfillment_id,
            "fulfillment_state": str(record.fulfillment_state),
        },
    )
    advance_execution_command(
        session,
        execution_command_set_id=fulfillment_set.execution_command_set_id,
        phase=phase,
        summary_text=event.summary,
        source_module_id="M-042",
        status=ExecutionCommandStatus.IN_PROGRESS if fulfillment_set.fulfillment_status != SupplierFulfillmentStatus.FAILED else ExecutionCommandStatus.ON_HOLD,
    )
    session.commit()
    session.refresh(event)
    return event


def get_supplier_fulfillment_set(
    session: Session,
    supplier_fulfillment_set_id: str,
) -> tuple[SupplierFulfillmentSet, list[tuple[SupplierFulfillmentRecord, list[SupplierFulfillmentEvent]]]]:
    fulfillment_set = _get_set(session, supplier_fulfillment_set_id)
    records = _get_records(session, supplier_fulfillment_set_id)
    return fulfillment_set, [(record, _get_events(session, record.supplier_fulfillment_id)) for record in records]


def list_supplier_fulfillment_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[SupplierFulfillmentSet, list[tuple[SupplierFulfillmentRecord, list[SupplierFulfillmentEvent]]]]]:
    query = select(SupplierFulfillmentSet).order_by(SupplierFulfillmentSet.created_at.desc())
    if deal_id:
        query = query.where(SupplierFulfillmentSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_supplier_fulfillment_set(session, item.supplier_fulfillment_set_id) for item in sets]


def get_supplier_fulfillment_record(
    session: Session,
    supplier_fulfillment_id: str,
) -> tuple[SupplierFulfillmentRecord, list[SupplierFulfillmentEvent]]:
    record = _get_record(session, supplier_fulfillment_id)
    return record, _get_events(session, supplier_fulfillment_id)
