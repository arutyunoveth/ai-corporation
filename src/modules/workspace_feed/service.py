from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.optimization.models import OptimizationRecommendationRecord
from src.modules.workspace_feed.models import WorkspaceFeedItem, WorkspaceFeedRecord, WorkspaceFeedSet
from src.modules.workspace_feed.schemas import BuildWorkspaceFeedRequest
from src.shared.control_package import (
    ensure_scope_exists,
    latest_copilot_context,
    latest_optimization_context,
    latest_workflow_context,
    resolve_scope_deal_id,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    CopilotFeedItemType,
    CopilotPriority,
    EventSeverity,
    OptimizationRecommendationType,
    WorkspaceItemType,
    WorkspacePriority,
    WorkspaceStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_workspace_feed_id, next_workspace_feed_set_id


def _get_set(session: Session, workspace_feed_set_id: str) -> WorkspaceFeedSet:
    record = session.scalar(
        select(WorkspaceFeedSet).where(WorkspaceFeedSet.workspace_feed_set_id == workspace_feed_set_id)
    )
    if not record:
        raise NotFoundError(f"Workspace feed set '{workspace_feed_set_id}' was not found")
    return record


def _get_record(session: Session, workspace_feed_id: str) -> WorkspaceFeedRecord:
    record = session.scalar(
        select(WorkspaceFeedRecord).where(WorkspaceFeedRecord.workspace_feed_id == workspace_feed_id)
    )
    if not record:
        raise NotFoundError(f"Workspace feed record '{workspace_feed_id}' was not found")
    return record


def _get_records(session: Session, workspace_feed_set_id: str) -> list[WorkspaceFeedRecord]:
    return list(
        session.scalars(
            select(WorkspaceFeedRecord)
            .where(WorkspaceFeedRecord.workspace_feed_set_id == workspace_feed_set_id)
            .order_by(WorkspaceFeedRecord.created_at.asc(), WorkspaceFeedRecord.id.asc())
        )
    )


def _get_items(session: Session, workspace_feed_id: str) -> list[WorkspaceFeedItem]:
    return list(
        session.scalars(
            select(WorkspaceFeedItem)
            .where(WorkspaceFeedItem.workspace_feed_id == workspace_feed_id)
            .order_by(WorkspaceFeedItem.created_at.asc(), WorkspaceFeedItem.id.asc())
        )
    )


def _priority_from_copilot(priority: CopilotPriority) -> WorkspacePriority:
    if priority == CopilotPriority.CRITICAL:
        return WorkspacePriority.CRITICAL
    if priority == CopilotPriority.HIGH:
        return WorkspacePriority.HIGH
    if priority == CopilotPriority.MEDIUM:
        return WorkspacePriority.MEDIUM
    return WorkspacePriority.LOW


def _item_type_from_copilot(item_type: CopilotFeedItemType) -> WorkspaceItemType:
    if item_type == CopilotFeedItemType.ALERT:
        return WorkspaceItemType.ALERT
    if item_type == CopilotFeedItemType.FOLLOW_UP:
        return WorkspaceItemType.FOLLOW_UP
    if item_type == CopilotFeedItemType.ACTION:
        return WorkspaceItemType.TASK
    if item_type == CopilotFeedItemType.RECOMMENDATION:
        return WorkspaceItemType.SUGGESTION
    return WorkspaceItemType.OTHER


def _decision_priority(record: OptimizationRecommendationRecord) -> WorkspacePriority:
    if record.recommendation_type in {
        OptimizationRecommendationType.RISK_REDUCTION,
        OptimizationRecommendationType.MARGIN,
    }:
        return WorkspacePriority.HIGH
    if record.recommendation_type in {
        OptimizationRecommendationType.CYCLE_TIME,
        OptimizationRecommendationType.SUPPLIER_STRATEGY,
    }:
        return WorkspacePriority.MEDIUM
    return WorkspacePriority.LOW


def build_workspace_feed(session: Session, payload: BuildWorkspaceFeedRequest) -> WorkspaceFeedSet:
    ensure_scope_exists(session, payload.scope_type, payload.scope_ref)
    feed_set = WorkspaceFeedSet(
        workspace_feed_set_id=next_workspace_feed_set_id(session, WorkspaceFeedSet.workspace_feed_set_id),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        workspace_status=WorkspaceStatus.BUILT,
    )
    session.add(feed_set)
    session.flush()
    deal_id = resolve_scope_deal_id(session, payload.scope_type, payload.scope_ref)
    try:
        workflow_set, workflow_record, workflow_steps = latest_workflow_context(
            session, payload.scope_type, payload.scope_ref
        )
        optimization_set, optimization_records, _ = latest_optimization_context(
            session, payload.scope_type, payload.scope_ref
        )
        copilot_set, copilot_record, copilot_items = latest_copilot_context(
            session, payload.scope_type, payload.scope_ref
        )
        if not workflow_set or not workflow_record:
            raise ValidationError("Workspace feed requires persisted workflow context")
        if not optimization_set or not optimization_records:
            raise ValidationError("Workspace feed requires persisted optimization context")
        if not copilot_set or not copilot_record:
            raise ValidationError("Workspace feed requires persisted copilot context")

        record = WorkspaceFeedRecord(
            workspace_feed_id=next_workspace_feed_id(session, WorkspaceFeedRecord.workspace_feed_id),
            workspace_feed_set_id=feed_set.workspace_feed_set_id,
            summary_text=(
                f"Workspace feed for {payload.scope_type}:{payload.scope_ref}: "
                f"workflow_steps={len(workflow_steps)}, copilot_items={len(copilot_items)}, "
                f"optimization_records={len(optimization_records)}."
            ),
        )
        session.add(record)
        session.flush()

        item_specs: list[dict] = []
        for item in copilot_items:
            item_specs.append(
                {
                    "item_code": item.item_code,
                    "item_type": _item_type_from_copilot(item.item_type),
                    "priority": _priority_from_copilot(item.priority),
                    "item_text": item.item_text,
                    "source_ref": item.source_ref or copilot_record.copilot_feed_id,
                }
            )

        summary_recommendation = next(
            (
                recommendation
                for recommendation in optimization_records
                if recommendation.recommendation_code == "OPTIMIZATION_SUMMARY"
            ),
            None,
        )
        if summary_recommendation:
            item_specs.append(
                {
                    "item_code": "OPTIMIZATION_DECISION",
                    "item_type": WorkspaceItemType.DECISION,
                    "priority": _decision_priority(summary_recommendation),
                    "item_text": summary_recommendation.recommendation_text,
                    "source_ref": summary_recommendation.optimization_recommendation_id,
                }
            )

        if not item_specs:
            item_specs.append(
                {
                    "item_code": "WORKSPACE_MONITOR_ONLY",
                    "item_type": WorkspaceItemType.OTHER,
                    "priority": WorkspacePriority.LOW,
                    "item_text": "Активных workspace items не найдено, оставить только мониторинг.",
                    "source_ref": workflow_set.workflow_run_set_id,
                }
            )

        for item in item_specs:
            feed_item = WorkspaceFeedItem(workspace_feed_id=record.workspace_feed_id, **item)
            session.add(feed_item)
            session.flush()
            append_event_record(
                session,
                deal_id=deal_id,
                event_code="workspace_feed_item_recorded",
                source_module_id="M-055",
                severity=EventSeverity.INFO,
                payload_json={
                    "workspace_feed_set_id": feed_set.workspace_feed_set_id,
                    "workspace_feed_id": record.workspace_feed_id,
                    "item_code": feed_item.item_code,
                    "item_type": feed_item.item_type,
                    "priority": feed_item.priority,
                },
            )

        append_event_record(
            session,
            deal_id=deal_id,
            event_code="workspace_feed_built",
            source_module_id="M-055",
            severity=EventSeverity.INFO,
            payload_json={
                "workspace_feed_set_id": feed_set.workspace_feed_set_id,
                "workspace_feed_id": record.workspace_feed_id,
                "item_count": len(item_specs),
            },
        )
        session.commit()
        session.refresh(feed_set)
        return feed_set
    except Exception as exc:
        feed_set.workspace_status = WorkspaceStatus.FAILED
        feed_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="workspace_feed_failed",
            source_module_id="M-055",
            severity=EventSeverity.HIGH,
            payload_json={"error": str(exc)},
        )
        session.commit()
        raise


def get_workspace_feed_set(
    session: Session,
    workspace_feed_set_id: str,
) -> tuple[WorkspaceFeedSet, list[tuple[WorkspaceFeedRecord, list[WorkspaceFeedItem]]]]:
    feed_set = _get_set(session, workspace_feed_set_id)
    records = [get_workspace_feed_record(session, item.workspace_feed_id) for item in _get_records(session, workspace_feed_set_id)]
    return feed_set, records


def get_workspace_feed_record(
    session: Session,
    workspace_feed_id: str,
) -> tuple[WorkspaceFeedRecord, list[WorkspaceFeedItem]]:
    record = _get_record(session, workspace_feed_id)
    return record, _get_items(session, workspace_feed_id)


def list_workspace_feed_sets(
    session: Session,
    *,
    scope_type: str | None = None,
    scope_ref: str | None = None,
) -> list[tuple[WorkspaceFeedSet, list[tuple[WorkspaceFeedRecord, list[WorkspaceFeedItem]]]]]:
    query = select(WorkspaceFeedSet).order_by(WorkspaceFeedSet.created_at.desc(), WorkspaceFeedSet.id.desc())
    if scope_type:
        query = query.where(WorkspaceFeedSet.scope_type == scope_type)
    if scope_ref:
        query = query.where(WorkspaceFeedSet.scope_ref == scope_ref)
    sets = list(session.scalars(query))
    return [get_workspace_feed_set(session, item.workspace_feed_set_id) for item in sets]
