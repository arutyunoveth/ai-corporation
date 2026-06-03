from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.delivery_launch.models import DeliveryLaunchSet
from src.modules.event_log.service import append_event_record
from src.modules.execution_command.service import advance_execution_command, get_execution_command_set
from src.modules.payment_collection.models import (
    PaymentCollectionEvent,
    PaymentCollectionRecord,
    PaymentCollectionSet,
)
from src.modules.payment_collection.schemas import (
    BuildPaymentCollectionRequest,
    RegisterPaymentCollectionEventRequest,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    CollectionState,
    EventSeverity,
    ExecutionCommandStatus,
    ExecutionPhase,
    PaymentCollectionStatus,
)
from src.shared.errors import NotFoundError
from src.shared.execution_package import load_execution_package
from src.shared.ids import (
    next_payment_collection_event_id,
    next_payment_collection_id,
    next_payment_collection_set_id,
)
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, payment_collection_set_id: str) -> PaymentCollectionSet:
    record = session.scalar(
        select(PaymentCollectionSet).where(PaymentCollectionSet.payment_collection_set_id == payment_collection_set_id)
    )
    if not record:
        raise NotFoundError(f"Payment collection set '{payment_collection_set_id}' was not found")
    return record


def _get_record(session: Session, payment_collection_id: str) -> PaymentCollectionRecord:
    record = session.scalar(
        select(PaymentCollectionRecord).where(PaymentCollectionRecord.payment_collection_id == payment_collection_id)
    )
    if not record:
        raise NotFoundError(f"Payment collection record '{payment_collection_id}' was not found")
    return record


def _get_records(session: Session, payment_collection_set_id: str) -> list[PaymentCollectionRecord]:
    return list(
        session.scalars(
            select(PaymentCollectionRecord)
            .where(PaymentCollectionRecord.payment_collection_set_id == payment_collection_set_id)
            .order_by(PaymentCollectionRecord.created_at.asc(), PaymentCollectionRecord.id.asc())
        )
    )


def _get_events(session: Session, payment_collection_id: str) -> list[PaymentCollectionEvent]:
    return list(
        session.scalars(
            select(PaymentCollectionEvent)
            .where(PaymentCollectionEvent.payment_collection_id == payment_collection_id)
            .order_by(PaymentCollectionEvent.event_timestamp.asc(), PaymentCollectionEvent.id.asc())
        )
    )


def build_payment_collection(session: Session, payload: BuildPaymentCollectionRequest) -> PaymentCollectionSet:
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
    expected_amount = payload.expected_amount
    collected_amount = payload.collected_amount if payload.collected_amount is not None else 0.0
    currency_code = payload.currency_code
    if package.recommended_quote:
        if expected_amount is None:
            expected_amount = package.recommended_quote.quoted_amount
        if currency_code is None:
            currency_code = package.recommended_quote.currency_code
    if expected_amount is None:
        expected_amount = 0.0
    if currency_code is None:
        currency_code = "RUB"

    collection_set = PaymentCollectionSet(
        payment_collection_set_id=next_payment_collection_set_id(
            session, PaymentCollectionSet.payment_collection_set_id
        ),
        deal_id=payload.deal_id,
        execution_command_set_id=execution_set.execution_command_set_id,
        collection_status=PaymentCollectionStatus.ACTIVE,
    )
    session.add(collection_set)
    session.flush()
    try:
        session.add(
            PaymentCollectionRecord(
                payment_collection_id=next_payment_collection_id(
                    session, PaymentCollectionRecord.payment_collection_id
                ),
                payment_collection_set_id=collection_set.payment_collection_set_id,
                invoice_ref=payload.invoice_ref,
                expected_amount=float(expected_amount),
                collected_amount=float(collected_amount),
                currency_code=currency_code.upper(),
                collection_state=CollectionState.NOT_INVOICED,
            )
        )
        collection_set.updated_at = utcnow()
        session.add(collection_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="payment_collection_built",
            source_module_id="M-044",
            severity=EventSeverity.INFO,
            payload_json={
                "payment_collection_set_id": collection_set.payment_collection_set_id,
                "execution_command_set_id": execution_set.execution_command_set_id,
            },
        )
        session.commit()
    except Exception as exc:
        collection_set.collection_status = PaymentCollectionStatus.FAILED
        collection_set.updated_at = utcnow()
        session.add(collection_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="payment_collection_failed",
            source_module_id="M-044",
            severity=EventSeverity.HIGH,
            payload_json={"payment_collection_set_id": collection_set.payment_collection_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(collection_set)
    return collection_set


def register_payment_collection_event(
    session: Session,
    payload: RegisterPaymentCollectionEventRequest,
) -> PaymentCollectionEvent:
    record = _get_record(session, payload.payment_collection_id)
    collection_set = _get_set(session, record.payment_collection_set_id)
    event = PaymentCollectionEvent(
        payment_collection_event_id=next_payment_collection_event_id(
            session, PaymentCollectionEvent.payment_collection_event_id
        ),
        payment_collection_id=record.payment_collection_id,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.collection_state:
        record.collection_state = payload.collection_state
    if payload.invoice_ref:
        record.invoice_ref = payload.invoice_ref
    if payload.collected_amount is not None:
        record.collected_amount = float(payload.collected_amount)
    record.updated_at = utcnow()

    if record.collection_state == CollectionState.INVOICED:
        collection_set.collection_status = PaymentCollectionStatus.INVOICED
        phase = ExecutionPhase.INVOICING
        status = ExecutionCommandStatus.IN_PROGRESS
    elif record.collection_state == CollectionState.PARTIAL:
        collection_set.collection_status = PaymentCollectionStatus.PARTIALLY_COLLECTED
        phase = ExecutionPhase.COLLECTION
        status = ExecutionCommandStatus.IN_PROGRESS
    elif record.collection_state == CollectionState.COLLECTED:
        collection_set.collection_status = PaymentCollectionStatus.COLLECTED
        phase = ExecutionPhase.COLLECTION
        status = ExecutionCommandStatus.COMPLETED
    elif record.collection_state == CollectionState.OVERDUE:
        collection_set.collection_status = PaymentCollectionStatus.FAILED
        phase = ExecutionPhase.COLLECTION
        status = ExecutionCommandStatus.ON_HOLD
    else:
        collection_set.collection_status = PaymentCollectionStatus.ACTIVE
        phase = ExecutionPhase.INVOICING
        status = ExecutionCommandStatus.IN_PROGRESS

    collection_set.updated_at = utcnow()
    session.add(record)
    session.add(collection_set)
    append_event_record(
        session,
        deal_id=collection_set.deal_id,
        event_code="payment_collection_event_recorded",
        source_module_id="M-044",
        severity=EventSeverity.INFO,
        payload_json={
            "payment_collection_set_id": collection_set.payment_collection_set_id,
            "payment_collection_id": record.payment_collection_id,
            "collection_state": str(record.collection_state),
            "collected_amount": record.collected_amount,
        },
    )
    advance_execution_command(
        session,
        execution_command_set_id=collection_set.execution_command_set_id,
        phase=phase,
        summary_text=event.summary,
        source_module_id="M-044",
        status=status,
    )
    session.commit()
    session.refresh(event)
    return event


def get_payment_collection_set(
    session: Session,
    payment_collection_set_id: str,
) -> tuple[PaymentCollectionSet, list[tuple[PaymentCollectionRecord, list[PaymentCollectionEvent]]]]:
    collection_set = _get_set(session, payment_collection_set_id)
    records = _get_records(session, payment_collection_set_id)
    return collection_set, [(record, _get_events(session, record.payment_collection_id)) for record in records]


def list_payment_collection_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[PaymentCollectionSet, list[tuple[PaymentCollectionRecord, list[PaymentCollectionEvent]]]]]:
    query = select(PaymentCollectionSet).order_by(PaymentCollectionSet.created_at.desc())
    if deal_id:
        query = query.where(PaymentCollectionSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_payment_collection_set(session, item.payment_collection_set_id) for item in sets]


def get_payment_collection_record(
    session: Session,
    payment_collection_id: str,
) -> tuple[PaymentCollectionRecord, list[PaymentCollectionEvent]]:
    record = _get_record(session, payment_collection_id)
    return record, _get_events(session, payment_collection_id)
