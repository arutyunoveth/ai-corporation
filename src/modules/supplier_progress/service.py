from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.supplier_progress.models import (
    SupplierProgressAlert,
    SupplierProgressEvent,
    SupplierProgressRecord,
    SupplierProgressSet,
)
from src.modules.supplier_progress.schemas import (
    BuildSupplierProgressRequest,
    RegisterSupplierProgressEventRequest,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    RiskSeverity,
    SupplierFulfillmentState,
    SupplierProgressEventType,
    SupplierProgressStatus,
    SupplierReadinessState,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.execution_entry_package import load_execution_entry_context
from src.shared.ids import (
    next_supplier_progress_event_id,
    next_supplier_progress_id,
    next_supplier_progress_set_id,
)
from src.shared.validation import require_non_empty


def _get_set(session: Session, supplier_progress_set_id: str) -> SupplierProgressSet:
    record = session.scalar(
        select(SupplierProgressSet).where(SupplierProgressSet.supplier_progress_set_id == supplier_progress_set_id)
    )
    if not record:
        raise NotFoundError(f"Supplier progress set '{supplier_progress_set_id}' was not found")
    return record


def _get_record(session: Session, supplier_progress_id: str) -> SupplierProgressRecord:
    record = session.scalar(
        select(SupplierProgressRecord).where(SupplierProgressRecord.supplier_progress_id == supplier_progress_id)
    )
    if not record:
        raise NotFoundError(f"Supplier progress record '{supplier_progress_id}' was not found")
    return record


def _get_records(session: Session, supplier_progress_set_id: str) -> list[SupplierProgressRecord]:
    return list(
        session.scalars(
            select(SupplierProgressRecord)
            .where(SupplierProgressRecord.supplier_progress_set_id == supplier_progress_set_id)
            .order_by(SupplierProgressRecord.created_at.asc(), SupplierProgressRecord.id.asc())
        )
    )


def _get_events(session: Session, supplier_progress_id: str) -> list[SupplierProgressEvent]:
    return list(
        session.scalars(
            select(SupplierProgressEvent)
            .where(SupplierProgressEvent.supplier_progress_id == supplier_progress_id)
            .order_by(SupplierProgressEvent.event_timestamp.asc(), SupplierProgressEvent.id.asc())
        )
    )


def _get_alerts(session: Session, supplier_progress_id: str) -> list[SupplierProgressAlert]:
    return list(
        session.scalars(
            select(SupplierProgressAlert)
            .where(SupplierProgressAlert.supplier_progress_id == supplier_progress_id)
            .order_by(SupplierProgressAlert.created_at.asc(), SupplierProgressAlert.id.asc())
        )
    )


def _progress_from_readiness(readiness_state: SupplierReadinessState) -> SupplierProgressStatus:
    if readiness_state == SupplierReadinessState.READY:
        return SupplierProgressStatus.COMPLETED
    if readiness_state in {SupplierReadinessState.DELAYED, SupplierReadinessState.BLOCKED}:
        return SupplierProgressStatus.AT_RISK if readiness_state == SupplierReadinessState.DELAYED else SupplierProgressStatus.FAILED
    return SupplierProgressStatus.ACTIVE


def _map_fulfillment_state(state: str | None) -> SupplierReadinessState:
    if state == SupplierFulfillmentState.FULFILLED:
        return SupplierReadinessState.READY
    if state == SupplierFulfillmentState.DELAYED:
        return SupplierReadinessState.DELAYED
    if state == SupplierFulfillmentState.FAILED:
        return SupplierReadinessState.BLOCKED
    if state == SupplierFulfillmentState.IN_PROGRESS:
        return SupplierReadinessState.IN_PROGRESS
    return SupplierReadinessState.NOT_STARTED


def build_supplier_progress(session: Session, payload: BuildSupplierProgressRequest) -> SupplierProgressSet:
    context = load_execution_entry_context(session, deal_id=payload.deal_id, supplier_id=payload.supplier_id)
    if not context.supplier_profile:
        raise ValidationError(f"Supplier '{payload.supplier_id}' does not exist")
    if not context.purchase_order_set or not context.purchase_order_record:
        raise ValidationError("Supplier progress monitor requires a canonical purchase order context")

    readiness_state = _map_fulfillment_state(
        str(context.supplier_fulfillment_record.fulfillment_state) if context.supplier_fulfillment_record else None
    )
    progress_set = SupplierProgressSet(
        supplier_progress_set_id=next_supplier_progress_set_id(session, SupplierProgressSet.supplier_progress_set_id),
        deal_id=payload.deal_id,
        supplier_id=payload.supplier_id,
        progress_status=_progress_from_readiness(readiness_state),
    )
    session.add(progress_set)
    session.flush()
    try:
        summary_text = (
            context.supplier_fulfillment_record.summary_text
            if context.supplier_fulfillment_record
            else "Supplier progress monitor opened from canonical purchase order without helper fulfillment updates yet."
        )
        record = SupplierProgressRecord(
            supplier_progress_id=next_supplier_progress_id(session, SupplierProgressRecord.supplier_progress_id),
            supplier_progress_set_id=progress_set.supplier_progress_set_id,
            readiness_state=readiness_state,
            summary_text=summary_text,
        )
        session.add(record)
        session.flush()

        if context.supplier_fulfillment_events:
            for helper_event in context.supplier_fulfillment_events:
                event_type = (
                    SupplierProgressEventType.DELAY
                    if context.supplier_fulfillment_record
                    and context.supplier_fulfillment_record.fulfillment_state == SupplierFulfillmentState.DELAYED
                    else SupplierProgressEventType.STATUS_UPDATE
                )
                session.add(
                    SupplierProgressEvent(
                        supplier_progress_event_id=next_supplier_progress_event_id(
                            session, SupplierProgressEvent.supplier_progress_event_id
                        ),
                        supplier_progress_id=record.supplier_progress_id,
                        event_type=event_type,
                        event_timestamp=helper_event.event_timestamp,
                        summary=helper_event.summary,
                        source_ref=helper_event.source_ref,
                    )
                )
                session.flush()
        else:
            session.add(
                SupplierProgressAlert(
                    supplier_progress_id=record.supplier_progress_id,
                    alert_code="SUPPLIER_UPDATE_PENDING",
                    severity=RiskSeverity.MEDIUM,
                    summary="No supplier fulfillment helper updates are persisted yet.",
                )
            )

        if readiness_state == SupplierReadinessState.DELAYED:
            session.add(
                SupplierProgressAlert(
                    supplier_progress_id=record.supplier_progress_id,
                    alert_code="SUPPLIER_DELAY",
                    severity=RiskSeverity.HIGH,
                    summary="Supplier helper context indicates delivery delay risk.",
                )
            )
        if readiness_state == SupplierReadinessState.BLOCKED:
            session.add(
                SupplierProgressAlert(
                    supplier_progress_id=record.supplier_progress_id,
                    alert_code="SUPPLIER_BLOCKED",
                    severity=RiskSeverity.CRITICAL,
                    summary="Supplier helper context indicates fulfillment failure.",
                )
            )

        progress_set.updated_at = utcnow()
        session.add(progress_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_progress_built",
            source_module_id="M-038",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_progress_set_id": progress_set.supplier_progress_set_id,
                "supplier_progress_id": record.supplier_progress_id,
                "supplier_id": payload.supplier_id,
            },
        )
        session.commit()
    except Exception as exc:
        progress_set.progress_status = SupplierProgressStatus.FAILED
        progress_set.updated_at = utcnow()
        session.add(progress_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_progress_failed",
            source_module_id="M-038",
            severity=EventSeverity.HIGH,
            payload_json={"supplier_progress_set_id": progress_set.supplier_progress_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(progress_set)
    return progress_set


def register_supplier_progress_event(session: Session, payload: RegisterSupplierProgressEventRequest) -> SupplierProgressEvent:
    record = _get_record(session, payload.supplier_progress_id)
    progress_set = _get_set(session, record.supplier_progress_set_id)
    event = SupplierProgressEvent(
        supplier_progress_event_id=next_supplier_progress_event_id(
            session, SupplierProgressEvent.supplier_progress_event_id
        ),
        supplier_progress_id=record.supplier_progress_id,
        event_type=payload.event_type,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref,
    )
    session.add(event)
    if payload.readiness_state:
        record.readiness_state = payload.readiness_state
    record.summary_text = event.summary
    record.updated_at = utcnow()
    progress_set.progress_status = _progress_from_readiness(record.readiness_state)
    progress_set.updated_at = utcnow()
    session.add(record)
    session.add(progress_set)

    if record.readiness_state in {SupplierReadinessState.DELAYED, SupplierReadinessState.BLOCKED}:
        session.add(
            SupplierProgressAlert(
                supplier_progress_id=record.supplier_progress_id,
                alert_code="MANUAL_PROGRESS_ALERT",
                severity=RiskSeverity.HIGH if record.readiness_state == SupplierReadinessState.DELAYED else RiskSeverity.CRITICAL,
                summary=event.summary,
            )
        )

    append_event_record(
        session,
        deal_id=progress_set.deal_id,
        event_code="supplier_progress_event_recorded",
        source_module_id="M-038",
        severity=EventSeverity.INFO,
        payload_json={
            "supplier_progress_set_id": progress_set.supplier_progress_set_id,
            "supplier_progress_id": record.supplier_progress_id,
            "readiness_state": str(record.readiness_state),
        },
    )
    session.commit()
    session.refresh(event)
    return event


def get_supplier_progress_set(
    session: Session,
    supplier_progress_set_id: str,
) -> tuple[SupplierProgressSet, list[tuple[SupplierProgressRecord, list[SupplierProgressEvent], list[SupplierProgressAlert]]]]:
    progress_set = _get_set(session, supplier_progress_set_id)
    records = _get_records(session, supplier_progress_set_id)
    return progress_set, [
        (record, _get_events(session, record.supplier_progress_id), _get_alerts(session, record.supplier_progress_id))
        for record in records
    ]


def list_supplier_progress_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[SupplierProgressSet, list[tuple[SupplierProgressRecord, list[SupplierProgressEvent], list[SupplierProgressAlert]]]]]:
    query = select(SupplierProgressSet).order_by(SupplierProgressSet.created_at.desc(), SupplierProgressSet.id.desc())
    if deal_id:
        query = query.where(SupplierProgressSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_supplier_progress_set(session, item.supplier_progress_set_id) for item in sets]


def get_supplier_progress_record(
    session: Session,
    supplier_progress_id: str,
) -> tuple[SupplierProgressRecord, list[SupplierProgressEvent], list[SupplierProgressAlert]]:
    record = _get_record(session, supplier_progress_id)
    return record, _get_events(session, supplier_progress_id), _get_alerts(session, supplier_progress_id)
