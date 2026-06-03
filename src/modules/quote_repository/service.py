from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.quote_repository.models import QuoteArtifactBinding, QuoteRecord, QuoteSet
from src.modules.quote_repository.schemas import RegisterQuoteRequest
from src.modules.rfq_generator.models import RFQBatch, RFQRecord
from src.modules.supplier_communications.models import SupplierCommunicationSet, SupplierCommunicationThread
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, QuoteStatus, RFQStatus, SupplierThreadStatus
from src.shared.errors import NotFoundError
from src.shared.ids import next_quote_id, next_quote_set_id
from src.shared.validation import require_non_empty, require_non_empty_list, require_positive_number, require_same_reference


def _get_rfq(session: Session, rfq_id: str) -> RFQRecord:
    rfq = session.scalar(select(RFQRecord).where(RFQRecord.rfq_id == rfq_id))
    if not rfq:
        raise NotFoundError(f"RFQ record '{rfq_id}' was not found")
    return rfq


def _get_thread(session: Session, supplier_thread_id: str) -> SupplierCommunicationThread:
    thread = session.scalar(
        select(SupplierCommunicationThread).where(SupplierCommunicationThread.supplier_thread_id == supplier_thread_id)
    )
    if not thread:
        raise NotFoundError(f"Supplier communication thread '{supplier_thread_id}' was not found")
    return thread


def _get_quote_set(session: Session, quote_set_id: str) -> QuoteSet:
    quote_set = session.scalar(select(QuoteSet).where(QuoteSet.quote_set_id == quote_set_id))
    if not quote_set:
        raise NotFoundError(f"Quote set '{quote_set_id}' was not found")
    return quote_set


def _get_quote(session: Session, quote_id: str) -> QuoteRecord:
    quote = session.scalar(select(QuoteRecord).where(QuoteRecord.quote_id == quote_id))
    if not quote:
        raise NotFoundError(f"Quote '{quote_id}' was not found")
    return quote


def _get_quote_artifacts(session: Session, quote_id: str) -> list[QuoteArtifactBinding]:
    return list(
        session.scalars(
            select(QuoteArtifactBinding)
            .where(QuoteArtifactBinding.quote_id == quote_id)
            .order_by(QuoteArtifactBinding.created_at.asc(), QuoteArtifactBinding.id.asc())
        )
    )


def _find_or_create_quote_set(session: Session, *, deal_id: str, rfq_batch_id: str) -> QuoteSet:
    existing = session.scalar(
        select(QuoteSet).where(QuoteSet.deal_id == deal_id, QuoteSet.rfq_batch_id == rfq_batch_id).order_by(QuoteSet.created_at.desc()).limit(1)
    )
    if existing:
        return existing
    quote_set = QuoteSet(
        quote_set_id=next_quote_set_id(session, QuoteSet.quote_set_id),
        deal_id=deal_id,
        rfq_batch_id=rfq_batch_id,
    )
    session.add(quote_set)
    session.flush()
    return quote_set


def register_quote(session: Session, payload: RegisterQuoteRequest) -> QuoteRecord:
    rfq = _get_rfq(session, payload.rfq_id)
    thread = _get_thread(session, payload.supplier_thread_id)
    require_same_reference(payload.supplier_id, rfq.supplier_id, "supplier_id")
    require_same_reference(payload.supplier_id, thread.supplier_id, "supplier_id")
    require_same_reference(payload.rfq_id, thread.rfq_id, "rfq_id")
    communication_set = session.scalar(
        select(SupplierCommunicationSet).where(
            SupplierCommunicationSet.supplier_communication_set_id == thread.supplier_communication_set_id
        )
    )
    if not communication_set:
        raise NotFoundError(f"Communication set for thread '{thread.supplier_thread_id}' was not found")
    require_same_reference(payload.deal_id, communication_set.deal_id, "deal_id")
    batch = session.scalar(select(RFQBatch).where(RFQBatch.rfq_batch_id == communication_set.rfq_batch_id))
    if not batch:
        raise NotFoundError(f"RFQ batch '{communication_set.rfq_batch_id}' was not found")
    quote_set = _find_or_create_quote_set(session, deal_id=payload.deal_id, rfq_batch_id=batch.rfq_batch_id)

    previous_quote = session.scalar(
        select(QuoteRecord)
        .where(QuoteRecord.quote_set_id == quote_set.quote_set_id, QuoteRecord.rfq_id == rfq.rfq_id, QuoteRecord.supplier_id == payload.supplier_id)
        .order_by(QuoteRecord.created_at.desc())
        .limit(1)
    )
    effective_status = payload.quote_status
    if previous_quote and payload.quote_status == QuoteStatus.RECEIVED:
        effective_status = QuoteStatus.REVISED

    quote = QuoteRecord(
        quote_id=next_quote_id(session, QuoteRecord.quote_id),
        quote_set_id=quote_set.quote_set_id,
        supplier_id=payload.supplier_id,
        rfq_id=rfq.rfq_id,
        supplier_thread_id=thread.supplier_thread_id,
        quote_status=effective_status,
        quoted_amount=float(require_positive_number(payload.quoted_amount, "quoted_amount")),
        currency_code=require_non_empty(payload.currency_code, "currency_code").upper(),
        quoted_at=payload.quoted_at or utcnow(),
        notes=payload.notes.strip() if payload.notes else None,
    )
    session.add(quote)
    session.flush()

    for artifact_ref in require_non_empty_list(payload.artifact_refs, "artifact_refs"):
        session.add(QuoteArtifactBinding(quote_id=quote.quote_id, artifact_ref=artifact_ref))

    thread.thread_status = SupplierThreadStatus.REPLIED
    thread.last_message_at = quote.quoted_at
    session.add(thread)
    rfq.rfq_status = RFQStatus.REPLIED
    rfq.updated_at = utcnow()
    session.add(rfq)

    event_code = "quote_registered"
    if effective_status == QuoteStatus.REVISED:
        event_code = "quote_revised"
    elif effective_status == QuoteStatus.WITHDRAWN:
        event_code = "quote_withdrawn"
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code=event_code,
        source_module_id="M-019",
        severity=EventSeverity.INFO,
        payload_json={
            "quote_id": quote.quote_id,
            "quote_set_id": quote_set.quote_set_id,
            "supplier_id": payload.supplier_id,
            "rfq_id": payload.rfq_id,
        },
    )
    session.commit()
    session.refresh(quote)
    return quote


def get_quote(session: Session, quote_id: str) -> tuple[QuoteRecord, list[QuoteArtifactBinding]]:
    quote = _get_quote(session, quote_id)
    return quote, _get_quote_artifacts(session, quote_id)


def list_quotes(session: Session, *, deal_id: str | None = None) -> list[tuple[QuoteRecord, list[QuoteArtifactBinding]]]:
    query = select(QuoteRecord).join(QuoteSet, QuoteSet.quote_set_id == QuoteRecord.quote_set_id).order_by(QuoteRecord.created_at.desc())
    if deal_id:
        query = query.where(QuoteSet.deal_id == deal_id)
    quotes = list(session.scalars(query))
    return [(quote, _get_quote_artifacts(session, quote.quote_id)) for quote in quotes]


def get_quote_set(session: Session, quote_set_id: str) -> tuple[QuoteSet, list[tuple[QuoteRecord, list[QuoteArtifactBinding]]]]:
    quote_set = _get_quote_set(session, quote_set_id)
    quotes = list(
        session.scalars(
            select(QuoteRecord).where(QuoteRecord.quote_set_id == quote_set_id).order_by(QuoteRecord.created_at.asc(), QuoteRecord.id.asc())
        )
    )
    return quote_set, [(quote, _get_quote_artifacts(session, quote.quote_id)) for quote in quotes]
