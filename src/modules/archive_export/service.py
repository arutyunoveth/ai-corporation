from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.archive_export.models import ArchiveExportItem, ArchiveExportRecord, ArchiveExportSet
from src.modules.archive_export.schemas import BuildArchiveExportRequest
from src.modules.bid_packages.models import BidPackageItem, BidPackageRecord, BidPackageSet
from src.modules.deal_closure.models import DealArchiveSnapshot, DealClosureSet
from src.modules.document_ingestion.models import DocumentSet, DocumentSetItem
from src.modules.event_log.service import append_event_record
from src.modules.kpi_learning.models import KPILearningSet
from src.modules.outcome_intake.models import OutcomeIntakeBinding
from src.modules.quote_repository.models import QuoteArtifactBinding, QuoteRecord, QuoteSet
from src.modules.submission_receipts.models import SubmissionReceiptBinding, SubmissionReceiptRecord, SubmissionReceiptSet
from src.shared.db.base import utcnow
from src.shared.enums import ArchiveExportItemRole, ArchiveExportStatus, DealClosureStatus, EventSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_archive_export_id, next_archive_export_set_id
from src.shared.validation import require_same_reference
from src.modules.outcome_intake.models import OutcomeIntakeRecord


def _get_set(session: Session, archive_export_set_id: str) -> ArchiveExportSet:
    record = session.scalar(select(ArchiveExportSet).where(ArchiveExportSet.archive_export_set_id == archive_export_set_id))
    if not record:
        raise NotFoundError(f"Archive export set '{archive_export_set_id}' was not found")
    return record


def _get_record(session: Session, archive_export_id: str) -> ArchiveExportRecord:
    record = session.scalar(select(ArchiveExportRecord).where(ArchiveExportRecord.archive_export_id == archive_export_id))
    if not record:
        raise NotFoundError(f"Archive export record '{archive_export_id}' was not found")
    return record


def _get_records(session: Session, archive_export_set_id: str) -> list[ArchiveExportRecord]:
    return list(
        session.scalars(
            select(ArchiveExportRecord)
            .where(ArchiveExportRecord.archive_export_set_id == archive_export_set_id)
            .order_by(ArchiveExportRecord.created_at.asc(), ArchiveExportRecord.id.asc())
        )
    )


def _get_items(session: Session, archive_export_id: str) -> list[ArchiveExportItem]:
    return list(
        session.scalars(
            select(ArchiveExportItem)
            .where(ArchiveExportItem.archive_export_id == archive_export_id)
            .order_by(ArchiveExportItem.created_at.asc(), ArchiveExportItem.id.asc())
        )
    )


def _collect_export_items(session: Session, deal_id: str, outcome_intake_set_id: str) -> list[dict]:
    items: dict[tuple[str, str], dict] = {}

    def add(artifact_ref: str | None, role: ArchiveExportItemRole) -> None:
        if not artifact_ref:
            return
        key = (artifact_ref, str(role))
        if key not in items:
            items[key] = {"artifact_ref": artifact_ref, "item_role": role}

    outcome_artifact_refs = list(
        session.scalars(
            select(OutcomeIntakeBinding.artifact_ref)
            .join(OutcomeIntakeRecord, OutcomeIntakeRecord.outcome_intake_id == OutcomeIntakeBinding.outcome_intake_id)
            .where(OutcomeIntakeRecord.outcome_intake_set_id == outcome_intake_set_id)
        )
    )
    for artifact_ref in outcome_artifact_refs:
        add(artifact_ref, ArchiveExportItemRole.DECISION)

    bid_artifact_refs = list(
        session.scalars(
            select(BidPackageItem.artifact_ref)
            .join(BidPackageRecord, BidPackageRecord.bid_package_id == BidPackageItem.bid_package_id)
            .join(BidPackageSet, BidPackageSet.bid_package_set_id == BidPackageRecord.bid_package_set_id)
            .where(BidPackageSet.deal_id == deal_id)
        )
    )
    for artifact_ref in bid_artifact_refs:
        add(artifact_ref, ArchiveExportItemRole.CORE_DOC)

    intake_artifact_refs = list(
        session.scalars(
            select(DocumentSetItem.artifact_ref)
            .join(DocumentSet, DocumentSet.document_set_id == DocumentSetItem.document_set_id)
            .where(DocumentSet.deal_id == deal_id)
        )
    )
    for artifact_ref in intake_artifact_refs:
        add(artifact_ref, ArchiveExportItemRole.CORE_DOC)

    receipt_artifact_refs = list(
        session.scalars(
            select(SubmissionReceiptBinding.artifact_ref)
            .join(SubmissionReceiptRecord, SubmissionReceiptRecord.submission_receipt_id == SubmissionReceiptBinding.submission_receipt_id)
            .join(
                SubmissionReceiptSet,
                SubmissionReceiptSet.submission_receipt_set_id == SubmissionReceiptRecord.submission_receipt_set_id,
            )
            .where(SubmissionReceiptSet.deal_id == deal_id)
        )
    )
    for artifact_ref in receipt_artifact_refs:
        add(artifact_ref, ArchiveExportItemRole.EVIDENCE)

    quote_artifact_refs = list(
        session.scalars(
            select(QuoteArtifactBinding.artifact_ref)
            .join(QuoteRecord, QuoteRecord.quote_id == QuoteArtifactBinding.quote_id)
            .join(QuoteSet, QuoteSet.quote_set_id == QuoteRecord.quote_set_id)
            .where(QuoteSet.deal_id == deal_id)
        )
    )
    for artifact_ref in quote_artifact_refs:
        add(artifact_ref, ArchiveExportItemRole.EXECUTION)

    return list(items.values())


def build_archive_export(session: Session, payload: BuildArchiveExportRequest) -> ArchiveExportSet:
    closure_set = session.scalar(
        select(DealClosureSet).where(DealClosureSet.deal_closure_set_id == payload.deal_closure_set_id)
    )
    if not closure_set:
        raise NotFoundError(f"Deal closure set '{payload.deal_closure_set_id}' was not found")
    require_same_reference(payload.deal_id, closure_set.deal_id, "deal_id")
    if str(closure_set.closure_status) != str(DealClosureStatus.CLOSED):
        raise ValidationError("Archive export requires a CLOSED deal closure set")

    archive_export_set = ArchiveExportSet(
        archive_export_set_id=next_archive_export_set_id(session, ArchiveExportSet.archive_export_set_id),
        deal_id=payload.deal_id,
        deal_closure_set_id=closure_set.deal_closure_set_id,
        export_status=ArchiveExportStatus.BUILT,
    )
    session.add(archive_export_set)
    session.flush()
    try:
        snapshot_ids = list(
            session.scalars(
                select(DealArchiveSnapshot.archive_snapshot_id).where(
                    DealArchiveSnapshot.deal_closure_set_id == closure_set.deal_closure_set_id
                )
            )
        )
        kpi_set_ids = list(
            session.scalars(
                select(KPILearningSet.kpi_learning_set_id).where(KPILearningSet.deal_id == payload.deal_id)
            )
        )
        collected_items = _collect_export_items(session, payload.deal_id, closure_set.outcome_intake_set_id)
        if payload.item_roles:
            allowed_roles = {str(role) for role in payload.item_roles}
            collected_items = [item for item in collected_items if str(item["item_role"]) in allowed_roles]

        manifest = {
            "deal_id": payload.deal_id,
            "deal_closure_set_id": closure_set.deal_closure_set_id,
            "archive_snapshot_ids": snapshot_ids,
            "kpi_learning_set_ids": kpi_set_ids,
            "item_count": len(collected_items),
            "exported_at": utcnow().isoformat() if payload.mark_exported else None,
        }
        export_record = ArchiveExportRecord(
            archive_export_id=next_archive_export_id(session, ArchiveExportRecord.archive_export_id),
            archive_export_set_id=archive_export_set.archive_export_set_id,
            export_manifest_json=manifest,
            export_format=payload.export_format,
        )
        session.add(export_record)
        session.flush()
        for item in collected_items:
            session.add(ArchiveExportItem(archive_export_id=export_record.archive_export_id, **item))
        archive_export_set.export_status = (
            ArchiveExportStatus.EXPORTED if payload.mark_exported else ArchiveExportStatus.BUILT
        )
        archive_export_set.updated_at = utcnow()
        session.add(archive_export_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="archive_export_built",
            source_module_id="M-049",
            severity=EventSeverity.INFO,
            payload_json={
                "archive_export_set_id": archive_export_set.archive_export_set_id,
                "archive_export_id": export_record.archive_export_id,
                "export_format": str(payload.export_format),
                "item_count": len(collected_items),
            },
        )
        if payload.mark_exported:
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="archive_export_marked_exported",
                source_module_id="M-049",
                severity=EventSeverity.INFO,
                payload_json={
                    "archive_export_set_id": archive_export_set.archive_export_set_id,
                    "archive_export_id": export_record.archive_export_id,
                },
            )
        session.commit()
    except Exception as exc:
        session.rollback()
        failed_set = ArchiveExportSet(
            archive_export_set_id=archive_export_set.archive_export_set_id,
            deal_id=payload.deal_id,
            deal_closure_set_id=closure_set.deal_closure_set_id,
            export_status=ArchiveExportStatus.FAILED,
        )
        session.add(failed_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="archive_export_failed",
            source_module_id="M-049",
            severity=EventSeverity.HIGH,
            payload_json={"archive_export_set_id": archive_export_set.archive_export_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(archive_export_set)
    return archive_export_set


def get_archive_export_set(
    session: Session,
    archive_export_set_id: str,
) -> tuple[ArchiveExportSet, list[tuple[ArchiveExportRecord, list[ArchiveExportItem]]]]:
    export_set = _get_set(session, archive_export_set_id)
    records = _get_records(session, archive_export_set_id)
    return export_set, [(record, _get_items(session, record.archive_export_id)) for record in records]


def list_archive_export_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ArchiveExportSet, list[tuple[ArchiveExportRecord, list[ArchiveExportItem]]]]]:
    query = select(ArchiveExportSet).order_by(ArchiveExportSet.created_at.desc())
    if deal_id:
        query = query.where(ArchiveExportSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_archive_export_set(session, item.archive_export_set_id) for item in sets]


def get_archive_export_record(
    session: Session,
    archive_export_id: str,
) -> tuple[ArchiveExportRecord, list[ArchiveExportItem]]:
    record = _get_record(session, archive_export_id)
    return record, _get_items(session, archive_export_id)
