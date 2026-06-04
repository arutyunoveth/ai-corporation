from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.bid_packages.models import BidPackageItem
from src.modules.bid_packages.service import get_bid_package_set
from src.modules.event_log.service import append_event_record
from src.modules.submission_archive.models import (
    SubmissionArchiveItem,
    SubmissionArchiveRecord,
    SubmissionArchiveSet,
)
from src.modules.submission_archive.schemas import BuildSubmissionArchiveRequest
from src.modules.submission_control.models import SubmissionExecutionRecord, SubmissionExecutionSet
from src.modules.submission_receipts.models import (
    SubmissionReceiptBinding,
    SubmissionReceiptRecord,
    SubmissionReceiptSet,
)
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, SubmissionArchiveItemRole, SubmissionArchiveStatus, SubmissionExecutionStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_submission_archive_id, next_submission_archive_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, submission_archive_set_id: str) -> SubmissionArchiveSet:
    record = session.scalar(
        select(SubmissionArchiveSet).where(SubmissionArchiveSet.submission_archive_set_id == submission_archive_set_id)
    )
    if not record:
        raise NotFoundError(f"Submission archive set '{submission_archive_set_id}' was not found")
    return record


def _get_record(session: Session, submission_archive_id: str) -> SubmissionArchiveRecord:
    record = session.scalar(
        select(SubmissionArchiveRecord).where(SubmissionArchiveRecord.submission_archive_id == submission_archive_id)
    )
    if not record:
        raise NotFoundError(f"Submission archive record '{submission_archive_id}' was not found")
    return record


def _get_records(session: Session, submission_archive_set_id: str) -> list[SubmissionArchiveRecord]:
    return list(
        session.scalars(
            select(SubmissionArchiveRecord)
            .where(SubmissionArchiveRecord.submission_archive_set_id == submission_archive_set_id)
            .order_by(SubmissionArchiveRecord.created_at.asc(), SubmissionArchiveRecord.id.asc())
        )
    )


def _get_items(session: Session, submission_archive_id: str) -> list[SubmissionArchiveItem]:
    return list(
        session.scalars(
            select(SubmissionArchiveItem)
            .where(SubmissionArchiveItem.submission_archive_id == submission_archive_id)
            .order_by(SubmissionArchiveItem.created_at.asc(), SubmissionArchiveItem.id.asc())
        )
    )


def _latest_submitted_execution(
    session: Session, *, deal_id: str, bid_package_set_id: str
) -> tuple[SubmissionExecutionSet, SubmissionExecutionRecord]:
    execution_set = session.scalar(
        select(SubmissionExecutionSet)
        .where(
            SubmissionExecutionSet.deal_id == deal_id,
            SubmissionExecutionSet.bid_package_set_id == bid_package_set_id,
            SubmissionExecutionSet.execution_status == SubmissionExecutionStatus.SUBMITTED,
        )
        .order_by(SubmissionExecutionSet.created_at.desc(), SubmissionExecutionSet.id.desc())
        .limit(1)
    )
    if not execution_set:
        raise ValidationError("Submission archive requires a SUBMITTED execution context")
    execution_record = session.scalar(
        select(SubmissionExecutionRecord)
        .where(SubmissionExecutionRecord.submission_execution_set_id == execution_set.submission_execution_set_id)
        .order_by(SubmissionExecutionRecord.started_at.desc(), SubmissionExecutionRecord.id.desc())
        .limit(1)
    )
    if not execution_record:
        raise ValidationError("Submission archive requires a persisted submission execution record")
    return execution_set, execution_record


def _latest_receipt_context(
    session: Session, *, deal_id: str, submission_execution_set_id: str
) -> tuple[SubmissionReceiptSet | None, SubmissionReceiptRecord | None, list[SubmissionReceiptBinding]]:
    receipt_set = session.scalar(
        select(SubmissionReceiptSet)
        .where(
            SubmissionReceiptSet.deal_id == deal_id,
            SubmissionReceiptSet.submission_execution_set_id == submission_execution_set_id,
        )
        .order_by(SubmissionReceiptSet.created_at.desc(), SubmissionReceiptSet.id.desc())
        .limit(1)
    )
    if not receipt_set:
        return None, None, []
    receipt_record = session.scalar(
        select(SubmissionReceiptRecord)
        .where(SubmissionReceiptRecord.submission_receipt_set_id == receipt_set.submission_receipt_set_id)
        .order_by(SubmissionReceiptRecord.receipt_timestamp.desc(), SubmissionReceiptRecord.id.desc())
        .limit(1)
    )
    if not receipt_record:
        return receipt_set, None, []
    bindings = list(
        session.scalars(
            select(SubmissionReceiptBinding)
            .where(SubmissionReceiptBinding.submission_receipt_id == receipt_record.submission_receipt_id)
            .order_by(SubmissionReceiptBinding.created_at.asc(), SubmissionReceiptBinding.id.asc())
        )
    )
    return receipt_set, receipt_record, bindings


def build_submission_archive(session: Session, payload: BuildSubmissionArchiveRequest) -> SubmissionArchiveSet:
    package_set, package_records = get_bid_package_set(session, payload.bid_package_set_id)
    require_same_reference(payload.deal_id, package_set.deal_id, "deal_id")
    if not package_records:
        raise ValidationError("Submission archive requires a persisted bid package record")
    execution_set, execution_record = _latest_submitted_execution(
        session, deal_id=payload.deal_id, bid_package_set_id=package_set.bid_package_set_id
    )
    receipt_set, receipt_record, receipt_bindings = _latest_receipt_context(
        session, deal_id=payload.deal_id, submission_execution_set_id=execution_set.submission_execution_set_id
    )
    package_record, package_items = package_records[-1]

    archive_set = SubmissionArchiveSet(
        submission_archive_set_id=next_submission_archive_set_id(
            session, SubmissionArchiveSet.submission_archive_set_id
        ),
        deal_id=payload.deal_id,
        archive_status=SubmissionArchiveStatus.BUILT if receipt_record else SubmissionArchiveStatus.PARTIAL,
    )
    session.add(archive_set)
    session.flush()
    try:
        manifest = {
            "bid_package_set_id": package_set.bid_package_set_id,
            "bid_package_id": package_record.bid_package_id,
            "package_item_count": len(package_items),
            "submission_execution_set_id": execution_set.submission_execution_set_id,
            "submission_execution_id": execution_record.submission_execution_id,
            "receipt_set_id": receipt_set.submission_receipt_set_id if receipt_set else None,
            "receipt_id": receipt_record.submission_receipt_id if receipt_record else None,
            "receipt_binding_count": len(receipt_bindings),
        }
        proof_summary = (
            f"Archive built from package {package_set.bid_package_set_id}; "
            f"submission execution {execution_set.submission_execution_set_id}; "
            f"receipt {'present' if receipt_record else 'missing'}."
        )
        record = SubmissionArchiveRecord(
            submission_archive_id=next_submission_archive_id(session, SubmissionArchiveRecord.submission_archive_id),
            submission_archive_set_id=archive_set.submission_archive_set_id,
            archive_manifest_json=manifest,
            proof_summary=proof_summary,
        )
        session.add(record)
        session.flush()
        for item in package_items:
            session.add(
                SubmissionArchiveItem(
                    submission_archive_id=record.submission_archive_id,
                    artifact_ref=item.artifact_ref,
                    item_role=SubmissionArchiveItemRole.BID_PACKAGE_ITEM,
                )
            )
        for binding in receipt_bindings:
            session.add(
                SubmissionArchiveItem(
                    submission_archive_id=record.submission_archive_id,
                    artifact_ref=binding.artifact_ref,
                    item_role=SubmissionArchiveItemRole.RECEIPT_EVIDENCE,
                )
            )
        archive_set.updated_at = utcnow()
        session.add(archive_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="submission_archive_built",
            source_module_id="M-032",
            severity=EventSeverity.INFO,
            payload_json={
                "submission_archive_set_id": archive_set.submission_archive_set_id,
                "submission_archive_id": record.submission_archive_id,
                "archive_status": str(archive_set.archive_status),
            },
        )
        session.commit()
    except Exception as exc:
        archive_set.archive_status = SubmissionArchiveStatus.FAILED
        archive_set.updated_at = utcnow()
        session.add(archive_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="submission_archive_failed",
            source_module_id="M-032",
            severity=EventSeverity.HIGH,
            payload_json={"submission_archive_set_id": archive_set.submission_archive_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(archive_set)
    return archive_set


def get_submission_archive_set(
    session: Session,
    submission_archive_set_id: str,
) -> tuple[SubmissionArchiveSet, list[tuple[SubmissionArchiveRecord, list[SubmissionArchiveItem]]]]:
    archive_set = _get_set(session, submission_archive_set_id)
    records = _get_records(session, submission_archive_set_id)
    return archive_set, [(record, _get_items(session, record.submission_archive_id)) for record in records]


def list_submission_archive_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[SubmissionArchiveSet, list[tuple[SubmissionArchiveRecord, list[SubmissionArchiveItem]]]]]:
    query = select(SubmissionArchiveSet).order_by(
        SubmissionArchiveSet.created_at.desc(), SubmissionArchiveSet.id.desc()
    )
    if deal_id:
        query = query.where(SubmissionArchiveSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_submission_archive_set(session, item.submission_archive_set_id) for item in sets]


def get_submission_archive_record(
    session: Session,
    submission_archive_id: str,
) -> tuple[SubmissionArchiveRecord, list[SubmissionArchiveItem]]:
    record = _get_record(session, submission_archive_id)
    return record, _get_items(session, submission_archive_id)
