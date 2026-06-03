from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.bid_documents.models import (
    BidDocumentCollectionBinding,
    BidDocumentCollectionRow,
    BidDocumentCollectionSet,
)
from src.modules.bid_documents.schemas import BuildBidDocumentCollectionRequest
from src.modules.ceo_approval.service import get_ceo_approval_set
from src.modules.document_requirements.service import get_document_requirement_set
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import (
    ApprovalDecision,
    BidDocumentCollectionStatus,
    BidDocumentRowStatus,
    DocumentRequirementStatus,
    EventSeverity,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_bid_document_collection_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, bid_document_collection_set_id: str) -> BidDocumentCollectionSet:
    record = session.scalar(
        select(BidDocumentCollectionSet).where(
            BidDocumentCollectionSet.bid_document_collection_set_id == bid_document_collection_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Bid document collection set '{bid_document_collection_set_id}' was not found")
    return record


def _get_rows(session: Session, bid_document_collection_set_id: str) -> list[BidDocumentCollectionRow]:
    return list(
        session.scalars(
            select(BidDocumentCollectionRow)
            .where(BidDocumentCollectionRow.bid_document_collection_set_id == bid_document_collection_set_id)
            .order_by(BidDocumentCollectionRow.created_at.asc(), BidDocumentCollectionRow.id.asc())
        )
    )


def _get_bindings(session: Session, bid_document_collection_set_id: str) -> list[BidDocumentCollectionBinding]:
    return list(
        session.scalars(
            select(BidDocumentCollectionBinding)
            .where(BidDocumentCollectionBinding.bid_document_collection_set_id == bid_document_collection_set_id)
            .order_by(BidDocumentCollectionBinding.created_at.asc(), BidDocumentCollectionBinding.id.asc())
        )
    )


def _derive_row_status(requirement_row, latest_decision: str | None) -> tuple[str, str | None]:
    has_artifact = bool(requirement_row.source_artifact_ref)
    status = str(requirement_row.requirement_status)

    if has_artifact:
        return BidDocumentRowStatus.COLLECTED, "Persisted source artifact is available for package assembly."
    if status == str(DocumentRequirementStatus.REQUIRED):
        return BidDocumentRowStatus.MISSING, "Required bid-prep artifact is not yet available."
    if status == str(DocumentRequirementStatus.OPTIONAL):
        return BidDocumentRowStatus.WAIVED, "Optional document is not required for the current package baseline."
    if status == str(DocumentRequirementStatus.CONDITIONAL):
        if latest_decision == str(ApprovalDecision.GO_WITH_CONDITIONS):
            return BidDocumentRowStatus.PENDING, "Conditional item should be collected before progressing to submission."
        return BidDocumentRowStatus.PENDING, "Conditional item is pending follow-up before package finalization."
    return BidDocumentRowStatus.PENDING, "Requirement needs manual classification before bid packaging."


def build_bid_document_collection(
    session: Session,
    payload: BuildBidDocumentCollectionRequest,
) -> BidDocumentCollectionSet:
    requirement_set, requirement_rows = get_document_requirement_set(session, payload.document_requirement_set_id)
    approval_set, approval_records = get_ceo_approval_set(session, payload.ceo_approval_set_id)
    require_same_reference(payload.deal_id, requirement_set.deal_id, "deal_id")
    require_same_reference(payload.deal_id, approval_set.deal_id, "deal_id")
    if not requirement_rows:
        raise ValidationError("Bid document collection requires persisted document requirement rows")

    latest_approval = approval_records[-1][0] if approval_records else None
    latest_decision = latest_approval.decision if latest_approval else None

    collection_set = BidDocumentCollectionSet(
        bid_document_collection_set_id=next_bid_document_collection_set_id(
            session, BidDocumentCollectionSet.bid_document_collection_set_id
        ),
        deal_id=payload.deal_id,
        document_requirement_set_id=requirement_set.document_requirement_set_id,
        ceo_approval_set_id=approval_set.ceo_approval_set_id,
        collection_status=BidDocumentCollectionStatus.BUILT,
    )
    session.add(collection_set)
    session.flush()
    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="bid_document_collection_started",
        source_module_id="M-029",
        severity=EventSeverity.INFO,
        payload_json={"bid_document_collection_set_id": collection_set.bid_document_collection_set_id},
    )
    try:
        statuses: list[str] = []
        for row in requirement_rows:
            row_status, notes = _derive_row_status(row, latest_decision)
            statuses.append(str(row_status))
            session.add(
                BidDocumentCollectionRow(
                    bid_document_collection_set_id=collection_set.bid_document_collection_set_id,
                    requirement_row_ref=row.row_code,
                    artifact_ref=row.source_artifact_ref,
                    collection_status=row_status,
                    notes=notes,
                )
            )
            session.add(
                BidDocumentCollectionBinding(
                    bid_document_collection_set_id=collection_set.bid_document_collection_set_id,
                    source_object_type="REQUIREMENT",
                    source_object_ref=f"{requirement_set.document_requirement_set_id}:{row.row_code}",
                )
            )
            if row.source_artifact_ref:
                session.add(
                    BidDocumentCollectionBinding(
                        bid_document_collection_set_id=collection_set.bid_document_collection_set_id,
                        source_object_type="ARTIFACT",
                        source_object_ref=row.source_artifact_ref,
                    )
                )

        session.add(
            BidDocumentCollectionBinding(
                bid_document_collection_set_id=collection_set.bid_document_collection_set_id,
                source_object_type="APPROVAL",
                source_object_ref=approval_set.ceo_approval_set_id,
            )
        )
        if latest_approval:
            session.add(
                BidDocumentCollectionBinding(
                    bid_document_collection_set_id=collection_set.bid_document_collection_set_id,
                    source_object_type="APPROVAL",
                    source_object_ref=latest_approval.ceo_approval_id,
                )
            )

        if any(status in {str(BidDocumentRowStatus.MISSING), str(BidDocumentRowStatus.PENDING)} for status in statuses):
            collection_set.collection_status = BidDocumentCollectionStatus.PARTIAL
        collection_set.updated_at = utcnow()
        session.add(collection_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="bid_document_collection_built",
            source_module_id="M-029",
            severity=EventSeverity.INFO,
            payload_json={
                "bid_document_collection_set_id": collection_set.bid_document_collection_set_id,
                "collection_status": str(collection_set.collection_status),
                "row_count": len(requirement_rows),
            },
        )
        session.commit()
    except Exception as exc:
        collection_set.collection_status = BidDocumentCollectionStatus.FAILED
        collection_set.updated_at = utcnow()
        session.add(collection_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="bid_document_collection_failed",
            source_module_id="M-029",
            severity=EventSeverity.HIGH,
            payload_json={
                "bid_document_collection_set_id": collection_set.bid_document_collection_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise
    session.refresh(collection_set)
    return collection_set


def get_bid_document_collection_set(
    session: Session,
    bid_document_collection_set_id: str,
) -> tuple[BidDocumentCollectionSet, list[BidDocumentCollectionRow], list[BidDocumentCollectionBinding]]:
    collection_set = _get_set(session, bid_document_collection_set_id)
    return (
        collection_set,
        _get_rows(session, bid_document_collection_set_id),
        _get_bindings(session, bid_document_collection_set_id),
    )


def list_bid_document_collection_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[BidDocumentCollectionSet, list[BidDocumentCollectionRow], list[BidDocumentCollectionBinding]]]:
    query = select(BidDocumentCollectionSet).order_by(BidDocumentCollectionSet.created_at.desc())
    if deal_id:
        query = query.where(BidDocumentCollectionSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_bid_document_collection_set(session, item.bid_document_collection_set_id) for item in sets]
