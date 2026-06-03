from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.deal_registry.service import get_deal
from src.modules.document_ingestion.models import DocumentIngestionRun, DocumentSet, DocumentSetItem
from src.modules.document_ingestion.schemas import CreateDocumentIngestionRunRequest, CreateDocumentSetRequest
from src.modules.document_store.models import ArtifactLink
from src.modules.document_store.service import get_artifact
from src.modules.event_log.service import append_event_record
from src.modules.tender_intake.service import get_tender_intake
from src.shared.db.base import utcnow
from src.shared.enums import DocumentIngestionRunStatus, DocumentIngestionStatus, EventSeverity
from src.shared.ids import next_document_set_id, next_ingestion_run_id
from src.shared.validation import require_non_empty, require_non_negative, require_same_reference


def _get_document_set(session: Session, document_set_id: str) -> DocumentSet:
    document_set = session.scalar(select(DocumentSet).where(DocumentSet.document_set_id == document_set_id))
    if not document_set:
        from src.shared.errors import NotFoundError

        raise NotFoundError(f"Document set '{document_set_id}' was not found")
    return document_set


def _get_document_set_items(session: Session, document_set_id: str) -> list[DocumentSetItem]:
    return list(
        session.scalars(
            select(DocumentSetItem)
            .where(DocumentSetItem.document_set_id == document_set_id)
            .order_by(DocumentSetItem.sort_order.asc(), DocumentSetItem.id.asc())
        )
    )


def _get_document_ingestion_runs(session: Session, document_set_id: str) -> list[DocumentIngestionRun]:
    return list(
        session.scalars(
            select(DocumentIngestionRun)
            .where(DocumentIngestionRun.document_set_id == document_set_id)
            .order_by(DocumentIngestionRun.started_at.asc(), DocumentIngestionRun.id.asc())
        )
    )


def create_document_set(session: Session, payload: CreateDocumentSetRequest) -> DocumentSet:
    deal = get_deal(session, payload.deal_id)
    intake, _ = get_tender_intake(session, payload.intake_id)
    require_same_reference(deal.deal_id, intake.deal_id, "deal_id")

    document_set = DocumentSet(
        document_set_id=next_document_set_id(session, DocumentSet.document_set_id),
        deal_id=payload.deal_id,
        intake_id=payload.intake_id,
        set_type=payload.set_type,
        ingestion_status=DocumentIngestionStatus.CREATED,
        item_count=len(payload.items),
    )
    session.add(document_set)
    session.flush()

    for item in payload.items:
        require_non_negative(item.sort_order, "sort_order")
        artifact = get_artifact(session, item.artifact_ref)
        if artifact.deal_id and artifact.deal_id != payload.deal_id:
            from src.shared.errors import ValidationError

            raise ValidationError("artifact_ref belongs to a different deal")
        session.add(
            DocumentSetItem(
                document_set_id=document_set.document_set_id,
                artifact_ref=artifact.artifact_ref,
                item_role=item.item_role,
                source_file_name=require_non_empty(item.source_file_name, "source_file_name"),
                sort_order=item.sort_order,
            )
        )
        session.add(
            ArtifactLink(
                artifact_ref=artifact.artifact_ref,
                linked_object_type="DOCUMENT_SET",
                linked_object_ref=document_set.document_set_id,
            )
        )

    append_event_record(
        session,
        deal_id=payload.deal_id,
        event_code="document_set_created",
        source_module_id="M-011",
        severity=EventSeverity.INFO,
        payload_json={"document_set_id": document_set.document_set_id, "item_count": document_set.item_count},
    )
    session.commit()
    session.refresh(document_set)
    return document_set


def get_document_set(session: Session, document_set_id: str) -> tuple[DocumentSet, list[DocumentSetItem], list[DocumentIngestionRun]]:
    document_set = _get_document_set(session, document_set_id)
    return document_set, _get_document_set_items(session, document_set_id), _get_document_ingestion_runs(session, document_set_id)


def list_document_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[DocumentSet, list[DocumentSetItem], list[DocumentIngestionRun]]]:
    query = select(DocumentSet).order_by(DocumentSet.created_at.desc())
    if deal_id:
        query = query.where(DocumentSet.deal_id == deal_id)
    document_sets = list(session.scalars(query))
    return [
        (document_set, _get_document_set_items(session, document_set.document_set_id), _get_document_ingestion_runs(session, document_set.document_set_id))
        for document_set in document_sets
    ]


def create_document_ingestion_run(
    session: Session,
    document_set_id: str,
    payload: CreateDocumentIngestionRunRequest,
) -> DocumentIngestionRun:
    document_set = _get_document_set(session, document_set_id)
    started_at = utcnow()
    finished_at = None if payload.run_status == DocumentIngestionRunStatus.STARTED else utcnow()
    run = DocumentIngestionRun(
        ingestion_run_id=next_ingestion_run_id(session, DocumentIngestionRun.ingestion_run_id),
        document_set_id=document_set.document_set_id,
        run_status=payload.run_status,
        started_at=started_at,
        finished_at=finished_at,
        notes=payload.notes,
    )
    session.add(run)

    event_code = "document_ingestion_started"
    if payload.run_status == DocumentIngestionRunStatus.COMPLETED:
        document_set.ingestion_status = DocumentIngestionStatus.INGESTED
        event_code = "document_ingestion_completed"
    elif payload.run_status == DocumentIngestionRunStatus.PARTIAL:
        document_set.ingestion_status = DocumentIngestionStatus.PARTIAL
        event_code = "document_ingestion_partial"
    elif payload.run_status == DocumentIngestionRunStatus.FAILED:
        document_set.ingestion_status = DocumentIngestionStatus.FAILED
        event_code = "document_ingestion_failed"

    if payload.run_status != DocumentIngestionRunStatus.STARTED:
        document_set.updated_at = utcnow()
        session.add(document_set)

    append_event_record(
        session,
        deal_id=document_set.deal_id,
        event_code=event_code,
        source_module_id="M-011",
        severity=EventSeverity.INFO if payload.run_status != DocumentIngestionRunStatus.FAILED else EventSeverity.HIGH,
        payload_json={
            "document_set_id": document_set.document_set_id,
            "ingestion_run_id": run.ingestion_run_id,
            "run_status": str(payload.run_status),
        },
    )
    session.commit()
    session.refresh(run)
    return run

