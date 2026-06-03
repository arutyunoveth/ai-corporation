from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.document_ingestion.service import get_document_set
from src.modules.event_log.service import append_event_record
from src.modules.rfq_generator.models import RFQArtifactBinding, RFQBatch, RFQRecord
from src.modules.rfq_generator.schemas import BuildRFQBatchRequest
from src.modules.supplier_search.service import get_supplier_shortlist
from src.modules.tender_summary.service import get_tender_summary
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, RFQBatchStatus, RFQStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_rfq_batch_id, next_rfq_id
from src.shared.validation import require_same_reference


def _get_rfq_batch(session: Session, rfq_batch_id: str) -> RFQBatch:
    batch = session.scalar(select(RFQBatch).where(RFQBatch.rfq_batch_id == rfq_batch_id))
    if not batch:
        raise NotFoundError(f"RFQ batch '{rfq_batch_id}' was not found")
    return batch


def _get_rfq_records(session: Session, rfq_batch_id: str) -> list[RFQRecord]:
    return list(
        session.scalars(
            select(RFQRecord).where(RFQRecord.rfq_batch_id == rfq_batch_id).order_by(RFQRecord.created_at.asc(), RFQRecord.id.asc())
        )
    )


def _get_rfq_artifact_refs(session: Session, rfq_id: str) -> list[str]:
    return list(
        session.scalars(
            select(RFQArtifactBinding.artifact_ref)
            .where(RFQArtifactBinding.rfq_id == rfq_id)
            .order_by(RFQArtifactBinding.created_at.asc(), RFQArtifactBinding.id.asc())
        )
    )


def _rfq_texts(summary, supplier_id: str) -> tuple[str, str]:
    title = summary.structured_summary_json.get("title") or "Закупка"
    customer_name = summary.structured_summary_json.get("customer_name") or "не указан"
    procurement_number = summary.structured_summary_json.get("procurement_number") or "не указан"
    subject = f"RFQ по закупке {procurement_number} для {supplier_id}"
    body = (
        f"Просим подготовить коммерческое предложение по закупке '{title}'. "
        f"Заказчик: {customer_name}. "
        f"Номер закупки: {procurement_number}. "
        f"Исходные документы и scope зарегистрированы в deal workspace."
    )
    return subject, body


def build_rfq_batch(session: Session, payload: BuildRFQBatchRequest) -> RFQBatch:
    shortlist, rows = get_supplier_shortlist(session, payload.supplier_shortlist_id)
    require_same_reference(payload.deal_id, shortlist.deal_id, "deal_id")
    summary, _ = get_tender_summary(session, shortlist.tender_summary_id)
    document_set, items, _ = get_document_set(session, shortlist.document_set_id)
    batch = RFQBatch(
        rfq_batch_id=next_rfq_batch_id(session, RFQBatch.rfq_batch_id),
        deal_id=payload.deal_id,
        supplier_shortlist_id=shortlist.supplier_shortlist_id,
        batch_status=RFQBatchStatus.BUILT,
    )
    session.add(batch)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="rfq_batch_build_started",
        source_module_id="M-017",
        severity=EventSeverity.INFO,
        payload_json={"rfq_batch_id": batch.rfq_batch_id, "supplier_shortlist_id": shortlist.supplier_shortlist_id},
    )
    try:
        if not rows:
            batch.batch_status = RFQBatchStatus.FAILED
            batch.updated_at = utcnow()
            session.add(batch)
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="rfq_batch_failed",
                source_module_id="M-017",
                severity=EventSeverity.HIGH,
                payload_json={"rfq_batch_id": batch.rfq_batch_id, "reason": "EMPTY_SHORTLIST"},
            )
            session.commit()
            session.refresh(batch)
            return batch

        for row in rows:
            subject, body = _rfq_texts(summary, row.supplier_id)
            rfq = RFQRecord(
                rfq_id=next_rfq_id(session, RFQRecord.rfq_id),
                rfq_batch_id=batch.rfq_batch_id,
                supplier_id=row.supplier_id,
                subject=subject,
                body_text=body,
                rfq_status=RFQStatus.BUILT,
            )
            session.add(rfq)
            session.flush()
            for item in items:
                session.add(RFQArtifactBinding(rfq_id=rfq.rfq_id, artifact_ref=item.artifact_ref))

        batch.batch_status = RFQBatchStatus.READY_TO_SEND if document_set.item_count > 0 else RFQBatchStatus.BUILT
        batch.updated_at = utcnow()
        session.add(batch)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="rfq_batch_built",
            source_module_id="M-017",
            severity=EventSeverity.INFO,
            payload_json={"rfq_batch_id": batch.rfq_batch_id, "rfq_count": len(rows)},
        )
        session.commit()
    except Exception as exc:
        batch.batch_status = RFQBatchStatus.FAILED
        batch.updated_at = utcnow()
        session.add(batch)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="rfq_batch_failed",
            source_module_id="M-017",
            severity=EventSeverity.HIGH,
            payload_json={"rfq_batch_id": batch.rfq_batch_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(batch)
    return batch


def get_rfq_batch(session: Session, rfq_batch_id: str) -> tuple[RFQBatch, list[tuple[RFQRecord, list[str]]]]:
    batch = _get_rfq_batch(session, rfq_batch_id)
    records = _get_rfq_records(session, rfq_batch_id)
    return batch, [(record, _get_rfq_artifact_refs(session, record.rfq_id)) for record in records]


def list_rfq_batches(session: Session, *, deal_id: str | None = None) -> list[tuple[RFQBatch, list[tuple[RFQRecord, list[str]]]]]:
    query = select(RFQBatch).order_by(RFQBatch.created_at.desc())
    if deal_id:
        query = query.where(RFQBatch.deal_id == deal_id)
    batches = list(session.scalars(query))
    return [(batch, [(record, _get_rfq_artifact_refs(session, record.rfq_id)) for record in _get_rfq_records(session, batch.rfq_batch_id)]) for batch in batches]


def get_rfq_record(session: Session, rfq_id: str) -> tuple[RFQRecord, list[str]]:
    record = session.scalar(select(RFQRecord).where(RFQRecord.rfq_id == rfq_id))
    if not record:
        raise NotFoundError(f"RFQ record '{rfq_id}' was not found")
    return record, _get_rfq_artifact_refs(session, rfq_id)
