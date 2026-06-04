from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.knowledge_assets.models import KnowledgeAssetLink, KnowledgeAssetRecord, KnowledgeAssetSet
from src.modules.knowledge_assets.schemas import BuildKnowledgeAssetRequest
from src.modules.postmortems.models import PostmortemFinding, PostmortemRecord, PostmortemSet
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, KnowledgeAssetStatus, KnowledgeAssetType
from src.shared.errors import NotFoundError, ValidationError
from src.shared.final_recovery_package import load_final_recovery_context
from src.shared.ids import next_knowledge_asset_id, next_knowledge_asset_set_id


def _get_set(session: Session, knowledge_asset_set_id: str) -> KnowledgeAssetSet:
    record = session.scalar(select(KnowledgeAssetSet).where(KnowledgeAssetSet.knowledge_asset_set_id == knowledge_asset_set_id))
    if not record:
        raise NotFoundError(f"Knowledge asset set '{knowledge_asset_set_id}' was not found")
    return record


def _get_record(session: Session, knowledge_asset_id: str) -> KnowledgeAssetRecord:
    record = session.scalar(select(KnowledgeAssetRecord).where(KnowledgeAssetRecord.knowledge_asset_id == knowledge_asset_id))
    if not record:
        raise NotFoundError(f"Knowledge asset record '{knowledge_asset_id}' was not found")
    return record


def _get_records(session: Session, knowledge_asset_set_id: str) -> list[KnowledgeAssetRecord]:
    return list(
        session.scalars(
            select(KnowledgeAssetRecord)
            .where(KnowledgeAssetRecord.knowledge_asset_set_id == knowledge_asset_set_id)
            .order_by(KnowledgeAssetRecord.created_at.asc(), KnowledgeAssetRecord.id.asc())
        )
    )


def _get_links(session: Session, knowledge_asset_id: str) -> list[KnowledgeAssetLink]:
    return list(
        session.scalars(
            select(KnowledgeAssetLink)
            .where(KnowledgeAssetLink.knowledge_asset_id == knowledge_asset_id)
            .order_by(KnowledgeAssetLink.created_at.asc(), KnowledgeAssetLink.id.asc())
        )
    )


def build_knowledge_asset(session: Session, payload: BuildKnowledgeAssetRequest) -> KnowledgeAssetSet:
    context = load_final_recovery_context(session, payload.deal_id)
    postmortem_set = session.scalar(
        select(PostmortemSet).where(PostmortemSet.deal_id == payload.deal_id).order_by(PostmortemSet.created_at.desc(), PostmortemSet.id.desc())
    )
    if not postmortem_set:
        raise ValidationError("Knowledge asset builder requires canonical postmortem context")
    postmortem_record = session.scalar(
        select(PostmortemRecord)
        .where(PostmortemRecord.postmortem_set_id == postmortem_set.postmortem_set_id)
        .order_by(PostmortemRecord.created_at.desc(), PostmortemRecord.id.desc())
    )
    if not postmortem_record:
        raise ValidationError("Knowledge asset builder requires postmortem record")
    findings = list(
        session.scalars(
            select(PostmortemFinding)
            .where(PostmortemFinding.postmortem_id == postmortem_record.postmortem_id)
            .order_by(PostmortemFinding.created_at.asc(), PostmortemFinding.id.asc())
        )
    )

    asset_set = KnowledgeAssetSet(
        knowledge_asset_set_id=next_knowledge_asset_set_id(session, KnowledgeAssetSet.knowledge_asset_set_id),
        deal_id=payload.deal_id,
        postmortem_set_id=postmortem_set.postmortem_set_id,
        archive_export_set_id=context.archive_export_set.archive_export_set_id if context.archive_export_set else None,
        dashboard_snapshot_set_id=context.dashboard_snapshot_set.dashboard_snapshot_set_id if context.dashboard_snapshot_set else None,
        knowledge_status=KnowledgeAssetStatus.READY if context.archive_export_set else KnowledgeAssetStatus.BUILT,
    )
    session.add(asset_set)
    session.flush()
    try:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="knowledge_asset_set_created",
            source_module_id="M-048",
            severity=EventSeverity.INFO,
            payload_json={"knowledge_asset_set_id": asset_set.knowledge_asset_set_id},
        )
        record = KnowledgeAssetRecord(
            knowledge_asset_id=next_knowledge_asset_id(session, KnowledgeAssetRecord.knowledge_asset_id),
            knowledge_asset_set_id=asset_set.knowledge_asset_set_id,
            asset_title=f"Knowledge asset for {payload.deal_id}",
            asset_type=KnowledgeAssetType.EXECUTION_LESSON,
            summary_text=postmortem_record.summary_text,
            asset_payload_json={
                "deal_id": payload.deal_id,
                "postmortem_id": postmortem_record.postmortem_id,
                "finding_codes": [item.finding_code for item in findings],
                "archive_export_set_id": asset_set.archive_export_set_id,
                "dashboard_snapshot_set_id": asset_set.dashboard_snapshot_set_id,
                "recommendation_summary": postmortem_record.recommendation_summary,
            },
        )
        session.add(record)
        session.flush()
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="knowledge_asset_record_created",
            source_module_id="M-048",
            severity=EventSeverity.INFO,
            payload_json={"knowledge_asset_set_id": asset_set.knowledge_asset_set_id, "knowledge_asset_id": record.knowledge_asset_id},
        )
        for source_ref in [
            postmortem_set.postmortem_set_id,
            asset_set.archive_export_set_id,
            asset_set.dashboard_snapshot_set_id,
            context.deal_closure_set.deal_closure_set_id if context.deal_closure_set else None,
        ]:
            if source_ref:
                session.add(KnowledgeAssetLink(knowledge_asset_id=record.knowledge_asset_id, source_ref=source_ref))
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="knowledge_asset_status_changed",
            source_module_id="M-048",
            severity=EventSeverity.INFO,
            payload_json={"knowledge_asset_set_id": asset_set.knowledge_asset_set_id, "knowledge_status": str(asset_set.knowledge_status)},
        )
        if not asset_set.archive_export_set_id or not asset_set.dashboard_snapshot_set_id:
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="knowledge_asset_exception_detected",
                source_module_id="M-048",
                severity=EventSeverity.WARNING,
                payload_json={"knowledge_asset_set_id": asset_set.knowledge_asset_set_id, "reason": "partial_source_context"},
            )
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="knowledge_asset_handoff_created",
            source_module_id="M-048",
            severity=EventSeverity.INFO,
            payload_json={"knowledge_asset_set_id": asset_set.knowledge_asset_set_id, "downstream_module_ids": ["M-049", "M-050"]},
        )
        asset_set.updated_at = utcnow()
        session.add(asset_set)
        session.commit()
    except Exception as exc:
        session.rollback()
        failed = session.scalar(
            select(KnowledgeAssetSet).where(KnowledgeAssetSet.knowledge_asset_set_id == asset_set.knowledge_asset_set_id)
        )
        if failed:
            failed.knowledge_status = KnowledgeAssetStatus.FAILED
            failed.updated_at = utcnow()
            session.add(failed)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="knowledge_asset_failed",
            source_module_id="M-048",
            severity=EventSeverity.HIGH,
            payload_json={"knowledge_asset_set_id": asset_set.knowledge_asset_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(asset_set)
    return asset_set


def get_knowledge_asset_set(
    session: Session,
    knowledge_asset_set_id: str,
) -> tuple[KnowledgeAssetSet, list[tuple[KnowledgeAssetRecord, list[KnowledgeAssetLink]]]]:
    asset_set = _get_set(session, knowledge_asset_set_id)
    records = _get_records(session, knowledge_asset_set_id)
    return asset_set, [(record, _get_links(session, record.knowledge_asset_id)) for record in records]


def list_knowledge_asset_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[KnowledgeAssetSet, list[tuple[KnowledgeAssetRecord, list[KnowledgeAssetLink]]]]]:
    query = select(KnowledgeAssetSet).order_by(KnowledgeAssetSet.created_at.desc(), KnowledgeAssetSet.id.desc())
    if deal_id:
        query = query.where(KnowledgeAssetSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_knowledge_asset_set(session, item.knowledge_asset_set_id) for item in sets]


def get_knowledge_asset_record(
    session: Session,
    knowledge_asset_id: str,
) -> tuple[KnowledgeAssetRecord, list[KnowledgeAssetLink]]:
    record = _get_record(session, knowledge_asset_id)
    return record, _get_links(session, knowledge_asset_id)
