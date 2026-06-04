from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.action_console.models import ActionConsoleItem, ActionConsoleRecord, ActionConsoleSet
from src.modules.action_console.schemas import BuildActionConsoleRequest
from src.modules.event_log.service import append_event_record
from src.shared.control_package import (
    ensure_scope_exists,
    latest_action_queue_context,
    latest_execution_ledger_context,
    latest_operator_session_context,
    resolve_scope_deal_id,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    ActionConsoleItemType,
    ActionConsolePriority,
    ActionConsoleStatus,
    ActionExecutionStatus,
    EventSeverity,
    ExecutionStatus,
    OperatorSessionItemStatus,
    OperatorSessionItemType,
    WorkspaceScopeType,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_action_console_id, next_action_console_set_id


def _get_set(session: Session, action_console_set_id: str) -> ActionConsoleSet:
    record = session.scalar(select(ActionConsoleSet).where(ActionConsoleSet.action_console_set_id == action_console_set_id))
    if not record:
        raise NotFoundError(f"Action console set '{action_console_set_id}' was not found")
    return record


def _get_record(session: Session, action_console_id: str) -> ActionConsoleRecord:
    record = session.scalar(select(ActionConsoleRecord).where(ActionConsoleRecord.action_console_id == action_console_id))
    if not record:
        raise NotFoundError(f"Action console record '{action_console_id}' was not found")
    return record


def _get_records(session: Session, action_console_set_id: str) -> list[ActionConsoleRecord]:
    return list(
        session.scalars(
            select(ActionConsoleRecord)
            .where(ActionConsoleRecord.action_console_set_id == action_console_set_id)
            .order_by(ActionConsoleRecord.created_at.asc(), ActionConsoleRecord.id.asc())
        )
    )


def _get_items(session: Session, action_console_id: str) -> list[ActionConsoleItem]:
    return list(
        session.scalars(
            select(ActionConsoleItem)
            .where(ActionConsoleItem.action_console_id == action_console_id)
            .order_by(ActionConsoleItem.created_at.asc(), ActionConsoleItem.id.asc())
        )
    )


def _queue_priority(action_status: str) -> ActionConsolePriority:
    if action_status == ActionExecutionStatus.PENDING:
        return ActionConsolePriority.CRITICAL
    if action_status == ActionExecutionStatus.APPROVED:
        return ActionConsolePriority.HIGH
    if action_status == ActionExecutionStatus.EXECUTED:
        return ActionConsolePriority.MEDIUM
    return ActionConsolePriority.LOW


def _session_priority(item_type: str, item_status: str) -> ActionConsolePriority:
    if item_type == OperatorSessionItemType.ALERT:
        return ActionConsolePriority.HIGH
    if item_status == OperatorSessionItemStatus.VISIBLE:
        return ActionConsolePriority.MEDIUM
    return ActionConsolePriority.LOW


def _execution_priority(execution_status: str) -> ActionConsolePriority:
    if execution_status == ExecutionStatus.FAILED:
        return ActionConsolePriority.CRITICAL
    if execution_status == ExecutionStatus.STARTED:
        return ActionConsolePriority.HIGH
    if execution_status == ExecutionStatus.SUCCEEDED:
        return ActionConsolePriority.MEDIUM
    return ActionConsolePriority.LOW


def build_action_console(session: Session, payload: BuildActionConsoleRequest) -> ActionConsoleSet:
    if payload.scope_type in {WorkspaceScopeType.DEAL, WorkspaceScopeType.EXECUTION}:
        ensure_scope_exists(session, payload.scope_type, payload.scope_ref)
    console_set = ActionConsoleSet(
        action_console_set_id=next_action_console_set_id(session, ActionConsoleSet.action_console_set_id),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        console_status=ActionConsoleStatus.BUILT,
    )
    session.add(console_set)
    session.flush()
    deal_id = resolve_scope_deal_id(session, payload.scope_type, payload.scope_ref)
    try:
        queue_set, queue_records = latest_action_queue_context(session, payload.scope_type, payload.scope_ref)
        operator_set, operator_record, operator_items = latest_operator_session_context(
            session, payload.scope_type, payload.scope_ref
        )
        ledger_set, ledger_records = latest_execution_ledger_context(session, payload.scope_type, payload.scope_ref)
        if not queue_set or not queue_records:
            raise ValidationError("Action console requires persisted action queue context")
        if not operator_set or not operator_record:
            raise ValidationError("Action console requires persisted operator session context")
        if not ledger_set or not ledger_records:
            raise ValidationError("Action console requires persisted execution ledger context")

        record = ActionConsoleRecord(
            action_console_id=next_action_console_id(session, ActionConsoleRecord.action_console_id),
            action_console_set_id=console_set.action_console_set_id,
            summary_text=(
                f"Action console for {payload.scope_type}:{payload.scope_ref}: "
                f"queue_items={len(queue_records)}, session_items={len(operator_items)}, "
                f"execution_candidates={len(ledger_records)}."
            ),
        )
        session.add(record)
        session.flush()

        item_specs: list[dict] = []
        for queue_record, _approvals in queue_records:
            item_specs.append(
                {
                    "item_code": queue_record.action_code,
                    "item_type": ActionConsoleItemType.QUEUE,
                    "priority": _queue_priority(queue_record.action_status),
                    "source_ref": queue_record.action_queue_id,
                    "item_text": queue_record.action_text,
                }
            )

        for item in operator_items:
            item_specs.append(
                {
                    "item_code": item.item_code,
                    "item_type": ActionConsoleItemType.SESSION,
                    "priority": _session_priority(item.item_type, item.item_status),
                    "source_ref": item.source_ref or operator_record.operator_session_id,
                    "item_text": f"Operator session item {item.item_code} is {item.item_status}.",
                }
            )

        for ledger_record, results in ledger_records:
            item_specs.append(
                {
                    "item_code": f"EXEC-{ledger_record.execution_ledger_id[-6:]}",
                    "item_type": ActionConsoleItemType.EXECUTION,
                    "priority": _execution_priority(ledger_record.execution_status),
                    "source_ref": ledger_record.execution_ledger_id,
                    "item_text": (
                        f"Execution candidate {ledger_record.execution_ledger_id} is {ledger_record.execution_status}; "
                        f"result_count={len(results)}."
                    ),
                }
            )

        failed_ledgers = [ledger for ledger, _results in ledger_records if ledger.execution_status == ExecutionStatus.FAILED]
        if failed_ledgers:
            item_specs.append(
                {
                    "item_code": "EXECUTION_ALERT",
                    "item_type": ActionConsoleItemType.ALERT,
                    "priority": ActionConsolePriority.CRITICAL,
                    "source_ref": failed_ledgers[0].execution_ledger_id,
                    "item_text": f"Detected {len(failed_ledgers)} failed internal execution candidates that need operator review.",
                }
            )

        for item in item_specs:
            console_item = ActionConsoleItem(action_console_id=record.action_console_id, **item)
            session.add(console_item)
            session.flush()
            append_event_record(
                session,
                deal_id=deal_id,
                event_code="action_console_item_recorded",
                source_module_id="M-061",
                severity=EventSeverity.INFO,
                payload_json={
                    "action_console_set_id": console_set.action_console_set_id,
                    "action_console_id": record.action_console_id,
                    "item_code": console_item.item_code,
                    "item_type": console_item.item_type,
                    "priority": console_item.priority,
                },
            )

        append_event_record(
            session,
            deal_id=deal_id,
            event_code="action_console_built",
            source_module_id="M-061",
            severity=EventSeverity.INFO,
            payload_json={
                "action_console_set_id": console_set.action_console_set_id,
                "action_console_id": record.action_console_id,
                "item_count": len(item_specs),
            },
        )
        session.commit()
        session.refresh(console_set)
        return console_set
    except Exception as exc:
        console_set.console_status = ActionConsoleStatus.FAILED
        console_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal_id,
            event_code="action_console_failed",
            source_module_id="M-061",
            severity=EventSeverity.HIGH,
            payload_json={"action_console_set_id": console_set.action_console_set_id, "error": str(exc)},
        )
        session.commit()
        raise


def get_action_console_set(
    session: Session,
    action_console_set_id: str,
) -> tuple[ActionConsoleSet, list[tuple[ActionConsoleRecord, list[ActionConsoleItem]]]]:
    console_set = _get_set(session, action_console_set_id)
    records = [(record, _get_items(session, record.action_console_id)) for record in _get_records(session, action_console_set_id)]
    return console_set, records


def get_action_console_record(
    session: Session,
    action_console_id: str,
) -> tuple[ActionConsoleRecord, list[ActionConsoleItem]]:
    record = _get_record(session, action_console_id)
    return record, _get_items(session, action_console_id)


def list_action_console_sets(
    session: Session,
    *,
    scope_type: WorkspaceScopeType | None = None,
    scope_ref: str | None = None,
) -> list[tuple[ActionConsoleSet, list[tuple[ActionConsoleRecord, list[ActionConsoleItem]]]]]:
    query = select(ActionConsoleSet).order_by(ActionConsoleSet.created_at.desc(), ActionConsoleSet.id.desc())
    if scope_type:
        query = query.where(ActionConsoleSet.scope_type == scope_type)
    if scope_ref:
        query = query.where(ActionConsoleSet.scope_ref == scope_ref)
    return [get_action_console_set(session, item.action_console_set_id) for item in session.scalars(query)]
