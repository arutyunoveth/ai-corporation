from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.rfq_generator.models import RFQBatch, RFQRecord
from src.modules.rfq_generator.service import get_rfq_batch
from src.modules.supplier_communications.models import (
    SupplierCommunicationSet,
    SupplierCommunicationThread,
    SupplierMessageRecord,
)
from src.modules.supplier_communications.schemas import BuildSupplierCommunicationSetRequest, RecordSupplierMessageRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, MessageDirection, RFQBatchStatus, RFQStatus, SupplierThreadStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_supplier_communication_set_id, next_supplier_message_id, next_supplier_thread_id
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, supplier_communication_set_id: str) -> SupplierCommunicationSet:
    record = session.scalar(
        select(SupplierCommunicationSet).where(
            SupplierCommunicationSet.supplier_communication_set_id == supplier_communication_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Supplier communication set '{supplier_communication_set_id}' was not found")
    return record


def _get_thread(session: Session, supplier_thread_id: str) -> SupplierCommunicationThread:
    thread = session.scalar(
        select(SupplierCommunicationThread).where(SupplierCommunicationThread.supplier_thread_id == supplier_thread_id)
    )
    if not thread:
        raise NotFoundError(f"Supplier communication thread '{supplier_thread_id}' was not found")
    return thread


def _get_threads(session: Session, supplier_communication_set_id: str) -> list[SupplierCommunicationThread]:
    return list(
        session.scalars(
            select(SupplierCommunicationThread)
            .where(SupplierCommunicationThread.supplier_communication_set_id == supplier_communication_set_id)
            .order_by(SupplierCommunicationThread.created_at.asc(), SupplierCommunicationThread.id.asc())
        )
    )


def _get_messages(session: Session, supplier_thread_id: str) -> list[SupplierMessageRecord]:
    return list(
        session.scalars(
            select(SupplierMessageRecord)
            .where(SupplierMessageRecord.supplier_thread_id == supplier_thread_id)
            .order_by(SupplierMessageRecord.sent_at.asc(), SupplierMessageRecord.id.asc())
        )
    )


def _get_rfq(session: Session, rfq_id: str) -> RFQRecord:
    rfq = session.scalar(select(RFQRecord).where(RFQRecord.rfq_id == rfq_id))
    if not rfq:
        raise NotFoundError(f"RFQ record '{rfq_id}' was not found")
    return rfq


def _sync_batch_send_status(session: Session, rfq_batch_id: str, deal_id: str) -> None:
    batch = session.scalar(select(RFQBatch).where(RFQBatch.rfq_batch_id == rfq_batch_id))
    if not batch:
        return
    statuses = list(session.scalars(select(RFQRecord.rfq_status).where(RFQRecord.rfq_batch_id == rfq_batch_id)))
    if statuses and all(status in {RFQStatus.SENT, RFQStatus.REPLIED, RFQStatus.CLOSED} for status in statuses):
        batch.batch_status = RFQBatchStatus.SENT
        batch.updated_at = utcnow()
        session.add(batch)
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="rfq_batch_sent",
            source_module_id="M-017",
            severity=EventSeverity.INFO,
            payload_json={"rfq_batch_id": rfq_batch_id},
        )
    elif any(status in {RFQStatus.SENT, RFQStatus.REPLIED, RFQStatus.CLOSED} for status in statuses):
        batch.batch_status = RFQBatchStatus.PARTIAL
        batch.updated_at = utcnow()
        session.add(batch)


def build_supplier_communication_set(session: Session, payload: BuildSupplierCommunicationSetRequest) -> SupplierCommunicationSet:
    batch, rfq_records = get_rfq_batch(session, payload.rfq_batch_id)
    require_same_reference(payload.deal_id, batch.deal_id, "deal_id")
    communication_set = SupplierCommunicationSet(
        supplier_communication_set_id=next_supplier_communication_set_id(
            session,
            SupplierCommunicationSet.supplier_communication_set_id,
        ),
        deal_id=payload.deal_id,
        rfq_batch_id=batch.rfq_batch_id,
    )
    session.add(communication_set)
    session.flush()
    for rfq_record, _ in rfq_records:
        thread = SupplierCommunicationThread(
            supplier_thread_id=next_supplier_thread_id(session, SupplierCommunicationThread.supplier_thread_id),
            supplier_communication_set_id=communication_set.supplier_communication_set_id,
            supplier_id=rfq_record.supplier_id,
            rfq_id=rfq_record.rfq_id,
            thread_status=SupplierThreadStatus.OPEN,
        )
        session.add(thread)
        session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="supplier_communication_set_created",
        source_module_id="M-018",
        severity=EventSeverity.INFO,
        payload_json={
            "supplier_communication_set_id": communication_set.supplier_communication_set_id,
            "rfq_batch_id": batch.rfq_batch_id,
            "thread_count": len(rfq_records),
        },
    )
    session.commit()
    session.refresh(communication_set)
    return communication_set


def get_supplier_communication_set(
    session: Session,
    supplier_communication_set_id: str,
) -> tuple[SupplierCommunicationSet, list[tuple[SupplierCommunicationThread, list[SupplierMessageRecord]]]]:
    communication_set = _get_set(session, supplier_communication_set_id)
    threads = _get_threads(session, supplier_communication_set_id)
    return communication_set, [(thread, _get_messages(session, thread.supplier_thread_id)) for thread in threads]


def list_supplier_communication_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[SupplierCommunicationSet, list[tuple[SupplierCommunicationThread, list[SupplierMessageRecord]]]]]:
    query = select(SupplierCommunicationSet).order_by(SupplierCommunicationSet.created_at.desc())
    if deal_id:
        query = query.where(SupplierCommunicationSet.deal_id == deal_id)
    records = list(session.scalars(query))
    return [get_supplier_communication_set(session, item.supplier_communication_set_id) for item in records]


def get_supplier_thread(
    session: Session,
    supplier_thread_id: str,
) -> tuple[SupplierCommunicationThread, list[SupplierMessageRecord]]:
    thread = _get_thread(session, supplier_thread_id)
    return thread, _get_messages(session, supplier_thread_id)


def record_supplier_message(
    session: Session,
    supplier_thread_id: str,
    payload: RecordSupplierMessageRequest,
) -> SupplierMessageRecord:
    thread = _get_thread(session, supplier_thread_id)
    communication_set = _get_set(session, thread.supplier_communication_set_id)
    rfq = _get_rfq(session, thread.rfq_id)
    require_same_reference(thread.supplier_id, rfq.supplier_id, "supplier_id")

    message = SupplierMessageRecord(
        supplier_message_id=next_supplier_message_id(session, SupplierMessageRecord.supplier_message_id),
        supplier_thread_id=thread.supplier_thread_id,
        direction=payload.direction,
        message_subject=payload.message_subject.strip() if payload.message_subject else None,
        message_text=require_non_empty(payload.message_text, "message_text"),
        linked_artifact_ref=payload.linked_artifact_ref,
        sent_at=payload.sent_at or utcnow(),
    )
    session.add(message)
    thread.last_message_at = message.sent_at
    if payload.direction == MessageDirection.OUTBOUND:
        thread.thread_status = SupplierThreadStatus.WAITING_REPLY
        rfq.rfq_status = RFQStatus.SENT
        event_code = "supplier_message_recorded"
    else:
        thread.thread_status = SupplierThreadStatus.REPLIED
        rfq.rfq_status = RFQStatus.REPLIED
        event_code = "supplier_reply_received"
    session.add(thread)
    rfq.updated_at = utcnow()
    session.add(rfq)
    _sync_batch_send_status(session, communication_set.rfq_batch_id, communication_set.deal_id)
    append_event_record(
        session,
        deal_id=communication_set.deal_id,
        event_code=event_code,
        source_module_id="M-018",
        severity=EventSeverity.INFO,
        payload_json={
            "supplier_message_id": message.supplier_message_id,
            "supplier_thread_id": thread.supplier_thread_id,
            "direction": str(payload.direction),
        },
    )
    session.commit()
    session.refresh(message)
    return message
