from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.integration_tasks.models import IntegrationTaskBinding, IntegrationTaskRecord, IntegrationTaskSet
from src.modules.integration_tasks.schemas import BuildIntegrationTaskRequest
from src.shared.control_package import (
    ensure_scope_exists,
    latest_action_queue_context,
    latest_connector_registry_context,
    latest_workspace_feed_context,
    resolve_scope_deal_id,
)
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import (
    ActionType,
    ConnectorStatus,
    ConnectorType,
    EventSeverity,
    IntegrationTaskBindingType,
    IntegrationTaskStatus,
    IntegrationTaskType,
    QueueApprovalStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_integration_task_id, next_integration_task_set_id


def _get_set(session: Session, integration_task_set_id: str) -> IntegrationTaskSet:
    record = session.scalar(
        select(IntegrationTaskSet).where(IntegrationTaskSet.integration_task_set_id == integration_task_set_id)
    )
    if not record:
        raise NotFoundError(f"Integration task set '{integration_task_set_id}' was not found")
    return record


def _get_record(session: Session, integration_task_id: str) -> IntegrationTaskRecord:
    record = session.scalar(
        select(IntegrationTaskRecord).where(IntegrationTaskRecord.integration_task_id == integration_task_id)
    )
    if not record:
        raise NotFoundError(f"Integration task record '{integration_task_id}' was not found")
    return record


def _get_records(session: Session, integration_task_set_id: str) -> list[IntegrationTaskRecord]:
    return list(
        session.scalars(
            select(IntegrationTaskRecord)
            .where(IntegrationTaskRecord.integration_task_set_id == integration_task_set_id)
            .order_by(IntegrationTaskRecord.created_at.asc(), IntegrationTaskRecord.id.asc())
        )
    )


def _get_bindings(session: Session, integration_task_id: str) -> list[IntegrationTaskBinding]:
    return list(
        session.scalars(
            select(IntegrationTaskBinding)
            .where(IntegrationTaskBinding.integration_task_id == integration_task_id)
            .order_by(IntegrationTaskBinding.created_at.asc(), IntegrationTaskBinding.id.asc())
        )
    )


def _is_approved(approvals: list) -> bool:
    return bool(approvals) and str(approvals[-1].approval_status) == str(QueueApprovalStatus.APPROVED)


def _task_type_for_action(action_type: str, connector_type: str) -> IntegrationTaskType:
    if action_type == ActionType.EMAIL_DRAFT:
        return IntegrationTaskType.EMAIL_SEND
    if action_type == ActionType.SYNC:
        if connector_type in {ConnectorType.CRM, ConnectorType.PORTAL}:
            return IntegrationTaskType.SYNC_PULL
        return IntegrationTaskType.SYNC_PUSH
    if action_type == ActionType.FOLLOW_UP:
        return IntegrationTaskType.FOLLOW_UP
    if action_type == ActionType.REBUILD:
        return IntegrationTaskType.EXPORT
    if action_type == ActionType.ESCALATE:
        return IntegrationTaskType.FOLLOW_UP
    return IntegrationTaskType.OTHER


def _pick_connector(connectors: list, action_type: str):
    active = [item for item in connectors if str(item.connector_status) == str(ConnectorStatus.ACTIVE)]
    if not active:
        raise ValidationError("Integration tasks require at least one ACTIVE connector")
    preferred: list[ConnectorType]
    if action_type in {ActionType.EMAIL_DRAFT, ActionType.FOLLOW_UP, ActionType.ESCALATE}:
        preferred = [ConnectorType.EMAIL, ConnectorType.CRM, ConnectorType.OTHER]
    elif action_type == ActionType.SYNC:
        preferred = [ConnectorType.CRM, ConnectorType.PORTAL, ConnectorType.SHEETS, ConnectorType.DRIVE]
    elif action_type == ActionType.REBUILD:
        preferred = [ConnectorType.DRIVE, ConnectorType.SHEETS, ConnectorType.PORTAL]
    else:
        preferred = [ConnectorType.OTHER, ConnectorType.DRIVE, ConnectorType.CRM]
    for connector_type in preferred:
        for connector in active:
            if str(connector.connector_type) == str(connector_type):
                return connector
    return active[0]


def build_integration_tasks(session: Session, payload: BuildIntegrationTaskRequest) -> IntegrationTaskSet:
    ensure_scope_exists(session, payload.scope_type, payload.scope_ref)
    task_set = IntegrationTaskSet(
        integration_task_set_id=next_integration_task_set_id(session, IntegrationTaskSet.integration_task_set_id),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        task_status=IntegrationTaskStatus.BUILT,
    )
    session.add(task_set)
    session.flush()
    deal_id = resolve_scope_deal_id(session, payload.scope_type, payload.scope_ref)
    try:
        connector_set, connectors = latest_connector_registry_context(session, payload.scope_type, payload.scope_ref)
        workspace_set, _workspace_record, _workspace_items = latest_workspace_feed_context(
            session, payload.scope_type, payload.scope_ref
        )
        queue_set, queue_records = latest_action_queue_context(session, payload.scope_type, payload.scope_ref)
        if not connector_set or not connectors:
            raise ValidationError("Integration task build requires persisted connector registry context")
        if not workspace_set:
            raise ValidationError("Integration task build requires persisted workspace feed context")
        if not queue_set or not queue_records:
            raise ValidationError("Integration task build requires persisted action queue context")

        approved_records = [(record, approvals) for record, approvals in queue_records if _is_approved(approvals)]
        if not approved_records:
            raise ValidationError("Integration task build requires approved action queue items")

        for record, approvals in approved_records:
            connector = _pick_connector(connectors, record.action_type)
            task_type = _task_type_for_action(record.action_type, connector.connector_type)
            task = IntegrationTaskRecord(
                integration_task_id=next_integration_task_id(session, IntegrationTaskRecord.integration_task_id),
                integration_task_set_id=task_set.integration_task_set_id,
                connector_registry_id=connector.connector_registry_id,
                action_queue_id=record.action_queue_id,
                task_type=task_type,
                task_payload_json={
                    "scope_type": payload.scope_type,
                    "scope_ref": payload.scope_ref,
                    "action_code": record.action_code,
                    "action_text": record.action_text,
                    "action_type": str(record.action_type),
                    "connector_code": connector.connector_code,
                    "connector_type": str(connector.connector_type),
                    "approval_status": str(approvals[-1].approval_status),
                },
            )
            session.add(task)
            session.flush()
            for source_ref, binding_type in (
                (record.action_queue_id, IntegrationTaskBindingType.QUEUE),
                (connector.connector_registry_id, IntegrationTaskBindingType.CONNECTOR),
                (record.source_ref or workspace_set.workspace_feed_set_id, IntegrationTaskBindingType.WORKSPACE),
            ):
                session.add(
                    IntegrationTaskBinding(
                        integration_task_id=task.integration_task_id,
                        source_ref=source_ref,
                        binding_type=binding_type,
                    )
                )
        task_set.task_status = IntegrationTaskStatus.READY
        task_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="integration_task_built",
            source_module_id="M-057",
            severity=EventSeverity.INFO,
            payload_json={
                "integration_task_set_id": task_set.integration_task_set_id,
                "connector_registry_set_id": connector_set.connector_registry_set_id,
                "workspace_feed_set_id": workspace_set.workspace_feed_set_id,
                "action_queue_set_id": queue_set.action_queue_set_id,
                "task_count": len(approved_records),
            },
        )
        session.commit()
        session.refresh(task_set)
        return task_set
    except Exception as exc:
        task_set.task_status = IntegrationTaskStatus.FAILED
        task_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="integration_task_failed",
            source_module_id="M-057",
            severity=EventSeverity.HIGH,
            payload_json={"integration_task_set_id": task_set.integration_task_set_id, "error": str(exc)},
        )
        session.commit()
        raise


def get_integration_task_set(
    session: Session,
    integration_task_set_id: str,
) -> tuple[IntegrationTaskSet, list[tuple[IntegrationTaskRecord, list[IntegrationTaskBinding]]]]:
    task_set = _get_set(session, integration_task_set_id)
    records = [get_integration_task_record(session, item.integration_task_id) for item in _get_records(session, integration_task_set_id)]
    return task_set, records


def get_integration_task_record(
    session: Session,
    integration_task_id: str,
) -> tuple[IntegrationTaskRecord, list[IntegrationTaskBinding]]:
    record = _get_record(session, integration_task_id)
    return record, _get_bindings(session, integration_task_id)


def list_integration_task_sets(
    session: Session,
    *,
    scope_type: str | None = None,
    scope_ref: str | None = None,
) -> list[tuple[IntegrationTaskSet, list[tuple[IntegrationTaskRecord, list[IntegrationTaskBinding]]]]]:
    query = select(IntegrationTaskSet).order_by(IntegrationTaskSet.created_at.desc(), IntegrationTaskSet.id.desc())
    if scope_type:
        query = query.where(IntegrationTaskSet.scope_type == scope_type)
    if scope_ref:
        query = query.where(IntegrationTaskSet.scope_ref == scope_ref)
    sets = list(session.scalars(query))
    return [get_integration_task_set(session, item.integration_task_set_id) for item in sets]
