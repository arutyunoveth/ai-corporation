from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.submission_control.service import get_submission_execution_set
from src.modules.submission_receipts.models import (
    SubmissionReceiptBinding,
    SubmissionReceiptRecord,
    SubmissionReceiptSet,
)
from src.modules.submission_receipts.schemas import RegisterSubmissionReceiptRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, SubmissionExecutionStatus, SubmissionReceiptStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_submission_receipt_id, next_submission_receipt_set_id
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, submission_receipt_set_id: str) -> SubmissionReceiptSet:
    record = session.scalar(
        select(SubmissionReceiptSet).where(SubmissionReceiptSet.submission_receipt_set_id == submission_receipt_set_id)
    )
    if not record:
        raise NotFoundError(f"Submission receipt set '{submission_receipt_set_id}' was not found")
    return record


def _get_record(session: Session, submission_receipt_id: str) -> SubmissionReceiptRecord:
    record = session.scalar(
        select(SubmissionReceiptRecord).where(SubmissionReceiptRecord.submission_receipt_id == submission_receipt_id)
    )
    if not record:
        raise NotFoundError(f"Submission receipt record '{submission_receipt_id}' was not found")
    return record


def _get_records(session: Session, submission_receipt_set_id: str) -> list[SubmissionReceiptRecord]:
    return list(
        session.scalars(
            select(SubmissionReceiptRecord)
            .where(SubmissionReceiptRecord.submission_receipt_set_id == submission_receipt_set_id)
            .order_by(SubmissionReceiptRecord.receipt_timestamp.asc(), SubmissionReceiptRecord.id.asc())
        )
    )


def _get_bindings(session: Session, submission_receipt_id: str) -> list[SubmissionReceiptBinding]:
    return list(
        session.scalars(
            select(SubmissionReceiptBinding)
            .where(SubmissionReceiptBinding.submission_receipt_id == submission_receipt_id)
            .order_by(SubmissionReceiptBinding.created_at.asc(), SubmissionReceiptBinding.id.asc())
        )
    )


def register_submission_receipt(session: Session, payload: RegisterSubmissionReceiptRequest) -> SubmissionReceiptSet:
    execution_set, execution_records = get_submission_execution_set(session, payload.submission_execution_set_id)
    require_same_reference(payload.deal_id, execution_set.deal_id, "deal_id")
    if str(execution_set.execution_status) != str(SubmissionExecutionStatus.SUBMITTED):
        raise ValidationError("Submission receipt can only be registered for a SUBMITTED execution set")
    if not execution_records:
        raise ValidationError("Submission receipt requires a persisted submission execution record")

    receipt_set = SubmissionReceiptSet(
        submission_receipt_set_id=next_submission_receipt_set_id(session, SubmissionReceiptSet.submission_receipt_set_id),
        deal_id=payload.deal_id,
        submission_execution_set_id=execution_set.submission_execution_set_id,
        receipt_status=SubmissionReceiptStatus.REGISTERED if payload.bindings else SubmissionReceiptStatus.PARTIAL,
    )
    session.add(receipt_set)
    session.flush()
    try:
        receipt_record = SubmissionReceiptRecord(
            submission_receipt_id=next_submission_receipt_id(session, SubmissionReceiptRecord.submission_receipt_id),
            submission_receipt_set_id=receipt_set.submission_receipt_set_id,
            receipt_number=require_non_empty(payload.receipt_number, "receipt_number"),
            receipt_timestamp=payload.receipt_timestamp,
            receipt_source=payload.receipt_source,
        )
        session.add(receipt_record)
        session.flush()
        for binding in payload.bindings:
            session.add(
                SubmissionReceiptBinding(
                    submission_receipt_id=receipt_record.submission_receipt_id,
                    artifact_ref=binding.artifact_ref,
                    binding_type=binding.binding_type,
                )
            )
        receipt_set.updated_at = utcnow()
        session.add(receipt_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="submission_receipt_registered",
            source_module_id="M-035",
            severity=EventSeverity.INFO,
            payload_json={
                "submission_receipt_set_id": receipt_set.submission_receipt_set_id,
                "submission_receipt_id": receipt_record.submission_receipt_id,
                "binding_count": len(payload.bindings),
            },
        )
        session.commit()
    except Exception as exc:
        receipt_set.receipt_status = SubmissionReceiptStatus.FAILED
        receipt_set.updated_at = utcnow()
        session.add(receipt_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="submission_receipt_failed",
            source_module_id="M-035",
            severity=EventSeverity.HIGH,
            payload_json={"submission_receipt_set_id": receipt_set.submission_receipt_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(receipt_set)
    return receipt_set


def get_submission_receipt_set(
    session: Session,
    submission_receipt_set_id: str,
) -> tuple[SubmissionReceiptSet, list[tuple[SubmissionReceiptRecord, list[SubmissionReceiptBinding]]]]:
    receipt_set = _get_set(session, submission_receipt_set_id)
    records = _get_records(session, submission_receipt_set_id)
    return receipt_set, [(record, _get_bindings(session, record.submission_receipt_id)) for record in records]


def list_submission_receipt_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[SubmissionReceiptSet, list[tuple[SubmissionReceiptRecord, list[SubmissionReceiptBinding]]]]]:
    query = select(SubmissionReceiptSet).order_by(SubmissionReceiptSet.created_at.desc())
    if deal_id:
        query = query.where(SubmissionReceiptSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_submission_receipt_set(session, item.submission_receipt_set_id) for item in sets]


def get_submission_receipt_record(
    session: Session,
    submission_receipt_id: str,
) -> tuple[SubmissionReceiptRecord, list[SubmissionReceiptBinding]]:
    record = _get_record(session, submission_receipt_id)
    return record, _get_bindings(session, submission_receipt_id)
