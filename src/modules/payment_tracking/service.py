from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.closing_docs.models import ClosingDocsSet
from src.modules.event_log.service import append_event_record
from src.modules.payment_tracking.models import (
    PaymentTrackingAlert,
    PaymentTrackingEvent,
    PaymentTrackingRecord,
    PaymentTrackingSet,
)
from src.modules.payment_tracking.schemas import (
    BuildPaymentTrackingRequest,
    RegisterPaymentTrackingEventRequest,
)
from src.shared.db.base import utcnow
from src.shared.delivery_recovery_package import load_delivery_helper_context
from src.shared.enums import (
    ClosingDocsStatus,
    EventSeverity,
    PaymentTrackingEventType,
    PaymentTrackingStatus,
    RiskSeverity,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_payment_tracking_event_id,
    next_payment_tracking_id,
    next_payment_tracking_set_id,
)
from src.shared.validation import require_non_empty


def _get_set(session: Session, payment_tracking_set_id: str) -> PaymentTrackingSet:
    record = session.scalar(select(PaymentTrackingSet).where(PaymentTrackingSet.payment_tracking_set_id == payment_tracking_set_id))
    if not record:
        raise NotFoundError(f"Payment tracking set '{payment_tracking_set_id}' was not found")
    return record


def _get_record(session: Session, payment_tracking_id: str) -> PaymentTrackingRecord:
    record = session.scalar(select(PaymentTrackingRecord).where(PaymentTrackingRecord.payment_tracking_id == payment_tracking_id))
    if not record:
        raise NotFoundError(f"Payment tracking record '{payment_tracking_id}' was not found")
    return record


def _get_records(session: Session, payment_tracking_set_id: str) -> list[PaymentTrackingRecord]:
    return list(
        session.scalars(
            select(PaymentTrackingRecord)
            .where(PaymentTrackingRecord.payment_tracking_set_id == payment_tracking_set_id)
            .order_by(PaymentTrackingRecord.created_at.asc(), PaymentTrackingRecord.id.asc())
        )
    )


def _get_events(session: Session, payment_tracking_id: str) -> list[PaymentTrackingEvent]:
    return list(
        session.scalars(
            select(PaymentTrackingEvent)
            .where(PaymentTrackingEvent.payment_tracking_id == payment_tracking_id)
            .order_by(PaymentTrackingEvent.event_timestamp.asc(), PaymentTrackingEvent.id.asc())
        )
    )


def _get_alerts(session: Session, payment_tracking_id: str) -> list[PaymentTrackingAlert]:
    return list(
        session.scalars(
            select(PaymentTrackingAlert)
            .where(PaymentTrackingAlert.payment_tracking_id == payment_tracking_id)
            .order_by(PaymentTrackingAlert.created_at.asc(), PaymentTrackingAlert.id.asc())
        )
    )


def _latest_closing_docs_set(session: Session, deal_id: str) -> ClosingDocsSet | None:
    return session.scalar(
        select(ClosingDocsSet)
        .where(ClosingDocsSet.deal_id == deal_id)
        .order_by(ClosingDocsSet.created_at.desc(), ClosingDocsSet.id.desc())
    )


def build_payment_tracking(session: Session, payload: BuildPaymentTrackingRequest) -> PaymentTrackingSet:
    closing_docs_set = _latest_closing_docs_set(session, payload.deal_id)
    if not closing_docs_set:
        raise ValidationError("Payment tracking requires canonical closing docs pack")

    helper_context = load_delivery_helper_context(session, payload.deal_id)
    expected_amount = 0.0
    paid_amount = 0.0
    overdue_days = 0
    payment_status = PaymentTrackingStatus.PENDING
    if helper_context.payment_record:
        expected_amount = float(helper_context.payment_record.expected_amount)
        paid_amount = float(helper_context.payment_record.collected_amount)
        if paid_amount >= expected_amount and expected_amount > 0:
            payment_status = PaymentTrackingStatus.PAID
        elif paid_amount > 0:
            payment_status = PaymentTrackingStatus.PARTIAL
        if str(helper_context.payment_record.collection_state) == "OVERDUE":
            overdue_days = 7
            payment_status = PaymentTrackingStatus.OVERDUE
    elif helper_context.execution_entry.supplier_quote:
        expected_amount = float(helper_context.execution_entry.supplier_quote.quoted_amount)

    tracking_set = PaymentTrackingSet(
        payment_tracking_set_id=next_payment_tracking_set_id(session, PaymentTrackingSet.payment_tracking_set_id),
        deal_id=payload.deal_id,
        payment_status=payment_status,
    )
    session.add(tracking_set)
    session.flush()
    try:
        record = PaymentTrackingRecord(
            payment_tracking_id=next_payment_tracking_id(session, PaymentTrackingRecord.payment_tracking_id),
            payment_tracking_set_id=tracking_set.payment_tracking_set_id,
            expected_amount=expected_amount,
            paid_amount=paid_amount,
            overdue_days=overdue_days,
            summary_text="Canonical payment tracking baseline created from collection and closing-docs context.",
        )
        session.add(record)
        session.flush()
        session.add(
            PaymentTrackingEvent(
                payment_tracking_event_id=next_payment_tracking_event_id(
                    session, PaymentTrackingEvent.payment_tracking_event_id
                ),
                payment_tracking_id=record.payment_tracking_id,
                event_type=PaymentTrackingEventType.INVOICED,
                event_timestamp=utcnow(),
                summary="Payment tracking baseline created.",
                source_ref=helper_context.payment_set.payment_collection_set_id if helper_context.payment_set else closing_docs_set.closing_docs_set_id,
            )
        )
        if closing_docs_set.docs_status != ClosingDocsStatus.READY:
            session.add(
                PaymentTrackingAlert(
                    payment_tracking_id=record.payment_tracking_id,
                    alert_code="CLOSING_DOCS_NOT_READY",
                    severity=RiskSeverity.MEDIUM,
                    summary="Closing docs pack is not fully ready for clean invoicing.",
                )
            )
        if payment_status == PaymentTrackingStatus.OVERDUE:
            session.add(
                PaymentTrackingAlert(
                    payment_tracking_id=record.payment_tracking_id,
                    alert_code="PAYMENT_OVERDUE",
                    severity=RiskSeverity.HIGH,
                    summary="Payment is overdue according to helper collection state.",
                )
            )
        elif payment_status in {PaymentTrackingStatus.PENDING, PaymentTrackingStatus.PARTIAL, PaymentTrackingStatus.PAID}:
            session.add(
                PaymentTrackingAlert(
                    payment_tracking_id=record.payment_tracking_id,
                    alert_code="PAYMENT_MONITORING",
                    severity=RiskSeverity.LOW,
                    summary="Payment tracker baseline is active.",
                )
            )
        tracking_set.updated_at = utcnow()
        session.add(tracking_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="payment_tracking_built",
            source_module_id="M-043",
            severity=EventSeverity.INFO,
            payload_json={
                "payment_tracking_set_id": tracking_set.payment_tracking_set_id,
                "payment_tracking_id": record.payment_tracking_id,
            },
        )
        session.commit()
    except Exception as exc:
        tracking_set.payment_status = PaymentTrackingStatus.DISPUTED
        tracking_set.updated_at = utcnow()
        session.add(tracking_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="payment_tracking_failed",
            source_module_id="M-043",
            severity=EventSeverity.HIGH,
            payload_json={"payment_tracking_set_id": tracking_set.payment_tracking_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(tracking_set)
    return tracking_set


def register_payment_tracking_event(
    session: Session,
    payload: RegisterPaymentTrackingEventRequest,
) -> PaymentTrackingEvent:
    record = _get_record(session, payload.payment_tracking_id)
    tracking_set = _get_set(session, record.payment_tracking_set_id)
    event = PaymentTrackingEvent(
        payment_tracking_event_id=next_payment_tracking_event_id(
            session, PaymentTrackingEvent.payment_tracking_event_id
        ),
        payment_tracking_id=record.payment_tracking_id,
        event_type=payload.event_type,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.expected_amount is not None:
        record.expected_amount = float(payload.expected_amount)
    if payload.paid_amount is not None:
        record.paid_amount = float(payload.paid_amount)
    if payload.overdue_days is not None:
        record.overdue_days = int(payload.overdue_days)
    if payload.payment_status:
        tracking_set.payment_status = payload.payment_status
    elif payload.event_type == PaymentTrackingEventType.PAID:
        tracking_set.payment_status = PaymentTrackingStatus.PAID
    elif payload.event_type == PaymentTrackingEventType.PARTIAL_PAYMENT:
        tracking_set.payment_status = PaymentTrackingStatus.PARTIAL
    elif payload.event_type == PaymentTrackingEventType.OVERDUE:
        tracking_set.payment_status = PaymentTrackingStatus.OVERDUE
    else:
        tracking_set.payment_status = PaymentTrackingStatus.PENDING

    if tracking_set.payment_status == PaymentTrackingStatus.OVERDUE:
        session.add(
            PaymentTrackingAlert(
                payment_tracking_id=record.payment_tracking_id,
                alert_code="PAYMENT_OVERDUE",
                severity=RiskSeverity.HIGH,
                summary=event.summary,
            )
        )
    record.summary_text = event.summary
    record.updated_at = utcnow()
    tracking_set.updated_at = utcnow()
    session.add(record)
    session.add(tracking_set)
    append_event_record(
        session,
        deal_id=tracking_set.deal_id,
        event_code="payment_tracking_event_recorded",
        source_module_id="M-043",
        severity=EventSeverity.INFO,
        payload_json={
            "payment_tracking_set_id": tracking_set.payment_tracking_set_id,
            "payment_tracking_id": record.payment_tracking_id,
            "event_type": str(payload.event_type),
            "payment_status": str(tracking_set.payment_status),
            "overdue_days": record.overdue_days,
        },
    )
    session.commit()
    session.refresh(event)
    return event


def get_payment_tracking_set(
    session: Session,
    payment_tracking_set_id: str,
) -> tuple[PaymentTrackingSet, list[tuple[PaymentTrackingRecord, list[PaymentTrackingEvent], list[PaymentTrackingAlert]]]]:
    tracking_set = _get_set(session, payment_tracking_set_id)
    records = _get_records(session, payment_tracking_set_id)
    return tracking_set, [
        (record, _get_events(session, record.payment_tracking_id), _get_alerts(session, record.payment_tracking_id))
        for record in records
    ]


def list_payment_tracking_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[PaymentTrackingSet, list[tuple[PaymentTrackingRecord, list[PaymentTrackingEvent], list[PaymentTrackingAlert]]]]]:
    query = select(PaymentTrackingSet).order_by(PaymentTrackingSet.created_at.desc(), PaymentTrackingSet.id.desc())
    if deal_id:
        query = query.where(PaymentTrackingSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_payment_tracking_set(session, item.payment_tracking_set_id) for item in sets]


def get_payment_tracking_record(
    session: Session,
    payment_tracking_id: str,
) -> tuple[PaymentTrackingRecord, list[PaymentTrackingEvent], list[PaymentTrackingAlert]]:
    record = _get_record(session, payment_tracking_id)
    return record, _get_events(session, payment_tracking_id), _get_alerts(session, payment_tracking_id)
