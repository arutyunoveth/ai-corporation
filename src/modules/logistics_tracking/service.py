from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.logistics_tracking.models import (
    LogisticsTrackingEvent,
    LogisticsTrackingLink,
    LogisticsTrackingRecord,
    LogisticsTrackingSet,
)
from src.modules.logistics_tracking.schemas import (
    BuildLogisticsTrackingRequest,
    RegisterLogisticsTrackingEventRequest,
)
from src.modules.purchase_orders.models import PurchaseOrderSet
from src.modules.supplier_progress.models import SupplierProgressSet
from src.shared.db.base import utcnow
from src.shared.delivery_recovery_package import load_delivery_helper_context
from src.shared.enums import (
    EventSeverity,
    LogisticsEventType,
    LogisticsStatus,
    ShippingAcceptanceState,
    SupplierReadinessState,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_logistics_tracking_event_id,
    next_logistics_tracking_id,
    next_logistics_tracking_set_id,
)
from src.shared.validation import require_non_empty


def _get_set(session: Session, logistics_tracking_set_id: str) -> LogisticsTrackingSet:
    record = session.scalar(
        select(LogisticsTrackingSet).where(
            LogisticsTrackingSet.logistics_tracking_set_id == logistics_tracking_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Logistics tracking set '{logistics_tracking_set_id}' was not found")
    return record


def _get_record(session: Session, logistics_tracking_id: str) -> LogisticsTrackingRecord:
    record = session.scalar(
        select(LogisticsTrackingRecord).where(LogisticsTrackingRecord.logistics_tracking_id == logistics_tracking_id)
    )
    if not record:
        raise NotFoundError(f"Logistics tracking record '{logistics_tracking_id}' was not found")
    return record


def _get_records(session: Session, logistics_tracking_set_id: str) -> list[LogisticsTrackingRecord]:
    return list(
        session.scalars(
            select(LogisticsTrackingRecord)
            .where(LogisticsTrackingRecord.logistics_tracking_set_id == logistics_tracking_set_id)
            .order_by(LogisticsTrackingRecord.created_at.asc(), LogisticsTrackingRecord.id.asc())
        )
    )


def _get_events(session: Session, logistics_tracking_id: str) -> list[LogisticsTrackingEvent]:
    return list(
        session.scalars(
            select(LogisticsTrackingEvent)
            .where(LogisticsTrackingEvent.logistics_tracking_id == logistics_tracking_id)
            .order_by(LogisticsTrackingEvent.event_timestamp.asc(), LogisticsTrackingEvent.id.asc())
        )
    )


def _get_links(session: Session, logistics_tracking_id: str) -> list[LogisticsTrackingLink]:
    return list(
        session.scalars(
            select(LogisticsTrackingLink)
            .where(LogisticsTrackingLink.logistics_tracking_id == logistics_tracking_id)
            .order_by(LogisticsTrackingLink.created_at.asc(), LogisticsTrackingLink.id.asc())
        )
    )


def _latest_purchase_order_set(session: Session, deal_id: str) -> PurchaseOrderSet | None:
    return session.scalar(
        select(PurchaseOrderSet)
        .where(PurchaseOrderSet.deal_id == deal_id)
        .order_by(PurchaseOrderSet.created_at.desc(), PurchaseOrderSet.id.desc())
    )


def _latest_supplier_progress_set(session: Session, deal_id: str) -> SupplierProgressSet | None:
    return session.scalar(
        select(SupplierProgressSet)
        .where(SupplierProgressSet.deal_id == deal_id)
        .order_by(SupplierProgressSet.created_at.desc(), SupplierProgressSet.id.desc())
    )


def _derive_status(helper_context) -> LogisticsStatus:
    shipping_record = helper_context.shipping_record
    if shipping_record:
        state = ShippingAcceptanceState(shipping_record.current_state)
        if state == ShippingAcceptanceState.ACCEPTED:
            return LogisticsStatus.ACCEPTED
        if state == ShippingAcceptanceState.DELIVERED:
            return LogisticsStatus.DELIVERED
        if state == ShippingAcceptanceState.REJECTED:
            return LogisticsStatus.FAILED
        if state == ShippingAcceptanceState.SHIPPED:
            return LogisticsStatus.IN_TRANSIT
    if helper_context.supplier_progress_record:
        readiness_state = SupplierReadinessState(helper_context.supplier_progress_record.readiness_state)
        if readiness_state == SupplierReadinessState.DELAYED:
            return LogisticsStatus.DELAYED
        if readiness_state == SupplierReadinessState.BLOCKED:
            return LogisticsStatus.FAILED
        if readiness_state in {SupplierReadinessState.IN_PROGRESS, SupplierReadinessState.READY}:
            return LogisticsStatus.IN_TRANSIT
    return LogisticsStatus.ACTIVE


def build_logistics_tracking(session: Session, payload: BuildLogisticsTrackingRequest) -> LogisticsTrackingSet:
    purchase_order_set = _latest_purchase_order_set(session, payload.deal_id)
    supplier_progress_set = _latest_supplier_progress_set(session, payload.deal_id)
    if not purchase_order_set:
        raise ValidationError("Logistics tracking requires a canonical purchase order")
    if not supplier_progress_set:
        raise ValidationError("Logistics tracking requires canonical supplier progress")

    helper_context = load_delivery_helper_context(session, payload.deal_id)
    logistics_set = LogisticsTrackingSet(
        logistics_tracking_set_id=next_logistics_tracking_set_id(
            session, LogisticsTrackingSet.logistics_tracking_set_id
        ),
        deal_id=payload.deal_id,
        logistics_status=_derive_status(helper_context),
    )
    session.add(logistics_set)
    session.flush()
    try:
        eta_at = utcnow() + timedelta(days=2)
        if helper_context.shipping_events:
            eta_at = helper_context.shipping_events[-1].event_timestamp + timedelta(days=2)
        record = LogisticsTrackingRecord(
            logistics_tracking_id=next_logistics_tracking_id(
                session, LogisticsTrackingRecord.logistics_tracking_id
            ),
            logistics_tracking_set_id=logistics_set.logistics_tracking_set_id,
            eta_at=eta_at,
            summary_text=(
                f"Canonical logistics dossier created for purchase order "
                f"{purchase_order_set.purchase_order_set_id}."
            ),
        )
        session.add(record)
        session.flush()
        session.add(
            LogisticsTrackingEvent(
                logistics_tracking_event_id=next_logistics_tracking_event_id(
                    session, LogisticsTrackingEvent.logistics_tracking_event_id
                ),
                logistics_tracking_id=record.logistics_tracking_id,
                event_type=LogisticsEventType.CREATED,
                event_timestamp=utcnow(),
                summary="Logistics tracking baseline created.",
                source_ref=helper_context.shipping_set.shipping_acceptance_set_id
                if helper_context.shipping_set
                else purchase_order_set.purchase_order_set_id,
            )
        )
        source_refs = {
            purchase_order_set.purchase_order_set_id,
            supplier_progress_set.supplier_progress_set_id,
        }
        if helper_context.execution_entry.execution_plan_set:
            source_refs.add(helper_context.execution_entry.execution_plan_set.execution_plan_set_id)
        if helper_context.shipping_record and helper_context.shipping_record.shipment_ref:
            source_refs.add(helper_context.shipping_record.shipment_ref)
        for source_ref in sorted(source_refs):
            session.add(LogisticsTrackingLink(logistics_tracking_id=record.logistics_tracking_id, source_ref=source_ref))
        logistics_set.updated_at = utcnow()
        session.add(logistics_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="logistics_tracking_built",
            source_module_id="M-039",
            severity=EventSeverity.INFO,
            payload_json={
                "logistics_tracking_set_id": logistics_set.logistics_tracking_set_id,
                "logistics_tracking_id": record.logistics_tracking_id,
            },
        )
        session.commit()
    except Exception as exc:
        logistics_set.logistics_status = LogisticsStatus.FAILED
        logistics_set.updated_at = utcnow()
        session.add(logistics_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="logistics_tracking_failed",
            source_module_id="M-039",
            severity=EventSeverity.HIGH,
            payload_json={"logistics_tracking_set_id": logistics_set.logistics_tracking_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(logistics_set)
    return logistics_set


def register_logistics_tracking_event(
    session: Session,
    payload: RegisterLogisticsTrackingEventRequest,
) -> LogisticsTrackingEvent:
    record = _get_record(session, payload.logistics_tracking_id)
    tracking_set = _get_set(session, record.logistics_tracking_set_id)
    event = LogisticsTrackingEvent(
        logistics_tracking_event_id=next_logistics_tracking_event_id(
            session, LogisticsTrackingEvent.logistics_tracking_event_id
        ),
        logistics_tracking_id=record.logistics_tracking_id,
        event_type=payload.event_type,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.eta_at:
        record.eta_at = payload.eta_at
    status = payload.logistics_status
    if not status:
        if payload.event_type == LogisticsEventType.ACCEPTED:
            status = LogisticsStatus.ACCEPTED
        elif payload.event_type == LogisticsEventType.DELIVERED:
            status = LogisticsStatus.DELIVERED
        elif payload.event_type == LogisticsEventType.DELAY:
            status = LogisticsStatus.DELAYED
        elif payload.event_type == LogisticsEventType.CHECKPOINT:
            status = LogisticsStatus.IN_TRANSIT
    if status:
        tracking_set.logistics_status = status
    if payload.source_ref:
        session.add(LogisticsTrackingLink(logistics_tracking_id=record.logistics_tracking_id, source_ref=payload.source_ref))
    record.summary_text = require_non_empty(payload.summary, "summary")
    record.updated_at = utcnow()
    tracking_set.updated_at = utcnow()
    session.add(record)
    session.add(tracking_set)
    append_event_record(
        session,
        deal_id=tracking_set.deal_id,
        event_code="logistics_tracking_event_recorded",
        source_module_id="M-039",
        severity=EventSeverity.INFO,
        payload_json={
            "logistics_tracking_set_id": tracking_set.logistics_tracking_set_id,
            "logistics_tracking_id": record.logistics_tracking_id,
            "event_type": str(payload.event_type),
            "logistics_status": str(tracking_set.logistics_status),
        },
    )
    session.commit()
    session.refresh(event)
    return event


def get_logistics_tracking_set(
    session: Session,
    logistics_tracking_set_id: str,
) -> tuple[LogisticsTrackingSet, list[tuple[LogisticsTrackingRecord, list[LogisticsTrackingEvent], list[LogisticsTrackingLink]]]]:
    tracking_set = _get_set(session, logistics_tracking_set_id)
    records = _get_records(session, logistics_tracking_set_id)
    return tracking_set, [
        (record, _get_events(session, record.logistics_tracking_id), _get_links(session, record.logistics_tracking_id))
        for record in records
    ]


def list_logistics_tracking_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[LogisticsTrackingSet, list[tuple[LogisticsTrackingRecord, list[LogisticsTrackingEvent], list[LogisticsTrackingLink]]]]]:
    query = select(LogisticsTrackingSet).order_by(
        LogisticsTrackingSet.created_at.desc(), LogisticsTrackingSet.id.desc()
    )
    if deal_id:
        query = query.where(LogisticsTrackingSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_logistics_tracking_set(session, item.logistics_tracking_set_id) for item in sets]


def get_logistics_tracking_record(
    session: Session,
    logistics_tracking_id: str,
) -> tuple[LogisticsTrackingRecord, list[LogisticsTrackingEvent], list[LogisticsTrackingLink]]:
    record = _get_record(session, logistics_tracking_id)
    return record, _get_events(session, logistics_tracking_id), _get_links(session, logistics_tracking_id)
