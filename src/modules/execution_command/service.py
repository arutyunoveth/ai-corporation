from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.delivery_launch.service import get_delivery_launch_set
from src.modules.event_log.service import append_event_record
from src.modules.execution_command.models import (
    ExecutionCommandBinding,
    ExecutionCommandRecord,
    ExecutionCommandSet,
)
from src.modules.execution_command.schemas import BuildExecutionCommandRequest
from src.shared.db.base import utcnow
from src.shared.enums import DeliveryLaunchStatus, EventSeverity, ExecutionCommandStatus, ExecutionPhase
from src.shared.errors import NotFoundError, ValidationError
from src.shared.execution_package import load_execution_package
from src.shared.ids import next_execution_command_id, next_execution_command_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, execution_command_set_id: str) -> ExecutionCommandSet:
    record = session.scalar(
        select(ExecutionCommandSet).where(ExecutionCommandSet.execution_command_set_id == execution_command_set_id)
    )
    if not record:
        raise NotFoundError(f"Execution command set '{execution_command_set_id}' was not found")
    return record


def _get_record(session: Session, execution_command_id: str) -> ExecutionCommandRecord:
    record = session.scalar(
        select(ExecutionCommandRecord).where(ExecutionCommandRecord.execution_command_id == execution_command_id)
    )
    if not record:
        raise NotFoundError(f"Execution command record '{execution_command_id}' was not found")
    return record


def _get_records(session: Session, execution_command_set_id: str) -> list[ExecutionCommandRecord]:
    return list(
        session.scalars(
            select(ExecutionCommandRecord)
            .where(ExecutionCommandRecord.execution_command_set_id == execution_command_set_id)
            .order_by(ExecutionCommandRecord.created_at.asc(), ExecutionCommandRecord.id.asc())
        )
    )


def _get_bindings(session: Session, execution_command_set_id: str) -> list[ExecutionCommandBinding]:
    return list(
        session.scalars(
            select(ExecutionCommandBinding)
            .where(ExecutionCommandBinding.execution_command_set_id == execution_command_set_id)
            .order_by(ExecutionCommandBinding.created_at.asc(), ExecutionCommandBinding.id.asc())
        )
    )


def build_execution_command(session: Session, payload: BuildExecutionCommandRequest) -> ExecutionCommandSet:
    launch_set, launch_records = get_delivery_launch_set(session, payload.delivery_launch_set_id)
    require_same_reference(payload.deal_id, launch_set.deal_id, "deal_id")
    if str(launch_set.launch_status) != str(DeliveryLaunchStatus.LAUNCHED):
        raise ValidationError("Execution command center can be opened only after delivery launch is LAUNCHED")
    if not launch_records:
        raise ValidationError("Delivery launch context has no persisted launch record")

    package = load_execution_package(
        session,
        deal_id=payload.deal_id,
        outcome_intake_set_id=launch_set.outcome_intake_set_id,
    )
    execution_set = ExecutionCommandSet(
        execution_command_set_id=next_execution_command_set_id(
            session, ExecutionCommandSet.execution_command_set_id
        ),
        deal_id=payload.deal_id,
        delivery_launch_set_id=launch_set.delivery_launch_set_id,
        execution_status=ExecutionCommandStatus.OPEN,
    )
    session.add(execution_set)
    session.flush()
    try:
        record = ExecutionCommandRecord(
            execution_command_id=next_execution_command_id(session, ExecutionCommandRecord.execution_command_id),
            execution_command_set_id=execution_set.execution_command_set_id,
            current_phase=ExecutionPhase.LAUNCHED,
            summary_text="Awarded deal entered execution contour after launch approval.",
        )
        session.add(record)
        session.flush()
        session.add(
            ExecutionCommandBinding(
                execution_command_set_id=execution_set.execution_command_set_id,
                source_object_type="OUTCOME",
                source_object_ref=package.outcome_set.outcome_intake_set_id,
            )
        )
        session.add(
            ExecutionCommandBinding(
                execution_command_set_id=execution_set.execution_command_set_id,
                source_object_type="LAUNCH",
                source_object_ref=launch_set.delivery_launch_set_id,
            )
        )
        if package.latest_bid_package_set:
            session.add(
                ExecutionCommandBinding(
                    execution_command_set_id=execution_set.execution_command_set_id,
                    source_object_type="PACKAGE",
                    source_object_ref=package.latest_bid_package_set.bid_package_set_id,
                )
            )
        if package.quote_recommendation:
            session.add(
                ExecutionCommandBinding(
                    execution_command_set_id=execution_set.execution_command_set_id,
                    source_object_type="SUPPLIER",
                    source_object_ref=package.quote_recommendation.recommended_supplier_id,
                )
            )
        execution_set.updated_at = utcnow()
        session.add(execution_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="execution_command_built",
            source_module_id="M-040",
            severity=EventSeverity.INFO,
            payload_json={
                "execution_command_set_id": execution_set.execution_command_set_id,
                "execution_command_id": record.execution_command_id,
            },
        )
        session.commit()
    except Exception as exc:
        execution_set.execution_status = ExecutionCommandStatus.FAILED
        execution_set.updated_at = utcnow()
        session.add(execution_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="execution_command_failed",
            source_module_id="M-040",
            severity=EventSeverity.HIGH,
            payload_json={"execution_command_set_id": execution_set.execution_command_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(execution_set)
    return execution_set


def advance_execution_command(
    session: Session,
    *,
    execution_command_set_id: str,
    phase: ExecutionPhase,
    summary_text: str,
    source_module_id: str,
    status: ExecutionCommandStatus | None = None,
) -> ExecutionCommandSet:
    execution_set = _get_set(session, execution_command_set_id)
    records = _get_records(session, execution_command_set_id)
    if not records:
        raise ValidationError("Execution command set has no persisted record")
    record = records[-1]
    record.current_phase = phase
    record.summary_text = summary_text
    record.updated_at = utcnow()
    execution_set.updated_at = utcnow()
    if status:
        execution_set.execution_status = status
    elif execution_set.execution_status == ExecutionCommandStatus.OPEN:
        execution_set.execution_status = ExecutionCommandStatus.IN_PROGRESS
    session.add(record)
    session.add(execution_set)
    append_event_record(
        session,
        deal_id=execution_set.deal_id,
        event_code="execution_command_updated",
        source_module_id=source_module_id,
        severity=EventSeverity.INFO,
        payload_json={
            "execution_command_set_id": execution_set.execution_command_set_id,
            "execution_command_id": record.execution_command_id,
            "current_phase": str(phase),
            "execution_status": str(execution_set.execution_status),
        },
    )
    return execution_set


def get_execution_command_set(
    session: Session,
    execution_command_set_id: str,
) -> tuple[ExecutionCommandSet, list[ExecutionCommandBinding], list[ExecutionCommandRecord]]:
    execution_set = _get_set(session, execution_command_set_id)
    return execution_set, _get_bindings(session, execution_command_set_id), _get_records(session, execution_command_set_id)


def list_execution_command_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ExecutionCommandSet, list[ExecutionCommandBinding], list[ExecutionCommandRecord]]]:
    query = select(ExecutionCommandSet).order_by(ExecutionCommandSet.created_at.desc())
    if deal_id:
        query = query.where(ExecutionCommandSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_execution_command_set(session, item.execution_command_set_id) for item in sets]


def get_execution_command_record(session: Session, execution_command_id: str) -> ExecutionCommandRecord:
    return _get_record(session, execution_command_id)
