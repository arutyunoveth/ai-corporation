from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.archive_export.models import ArchiveExportSet
from src.modules.deal_closure.models import DealClosureSet
from src.modules.deal_registry.models import Deal
from src.modules.event_log.service import append_event_record
from src.modules.execution_command.models import ExecutionCommandRecord, ExecutionCommandSet
from src.modules.incidents.models import IncidentRecord, IncidentSet
from src.modules.learning_automation.models import LearningAutomationSet
from src.modules.outcome_intake.models import OutcomeIntakeRecord, OutcomeIntakeSet
from src.modules.payment_collection.models import PaymentCollectionRecord, PaymentCollectionSet
from src.modules.shipping_acceptance.models import ShippingAcceptanceRecord, ShippingAcceptanceSet
from src.modules.workflow_runs.models import WorkflowRunRecord, WorkflowRunSet, WorkflowStepRecord
from src.modules.workflow_runs.schemas import BuildWorkflowRunRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, WorkflowScopeType, WorkflowStatus, WorkflowStepStatus, WorkflowStepType
from src.shared.errors import NotFoundError
from src.shared.ids import next_workflow_run_id, next_workflow_run_set_id, next_workflow_step_id


def _get_set(session: Session, workflow_run_set_id: str) -> WorkflowRunSet:
    record = session.scalar(select(WorkflowRunSet).where(WorkflowRunSet.workflow_run_set_id == workflow_run_set_id))
    if not record:
        raise NotFoundError(f"Workflow run set '{workflow_run_set_id}' was not found")
    return record


def _get_record(session: Session, workflow_run_id: str) -> WorkflowRunRecord:
    record = session.scalar(select(WorkflowRunRecord).where(WorkflowRunRecord.workflow_run_id == workflow_run_id))
    if not record:
        raise NotFoundError(f"Workflow run record '{workflow_run_id}' was not found")
    return record


def _get_records(session: Session, workflow_run_set_id: str) -> list[WorkflowRunRecord]:
    return list(
        session.scalars(
            select(WorkflowRunRecord)
            .where(WorkflowRunRecord.workflow_run_set_id == workflow_run_set_id)
            .order_by(WorkflowRunRecord.created_at.asc(), WorkflowRunRecord.id.asc())
        )
    )


def _get_steps(session: Session, workflow_run_id: str) -> list[WorkflowStepRecord]:
    return list(
        session.scalars(
            select(WorkflowStepRecord)
            .where(WorkflowStepRecord.workflow_run_id == workflow_run_id)
            .order_by(WorkflowStepRecord.created_at.asc(), WorkflowStepRecord.id.asc())
        )
    )


def _latest_dashboard_exists(session: Session, scope_type: str, scope_ref: str) -> bool:
    from src.modules.dashboard_snapshots.models import DashboardSnapshotSet

    return (
        session.scalar(
            select(DashboardSnapshotSet.id)
            .where(DashboardSnapshotSet.scope_type == scope_type, DashboardSnapshotSet.scope_ref == scope_ref)
            .order_by(DashboardSnapshotSet.created_at.desc(), DashboardSnapshotSet.id.desc())
            .limit(1)
        )
        is not None
    )


def _make_step(
    step_code: str,
    step_type: WorkflowStepType,
    step_status: WorkflowStepStatus,
    *,
    source_ref: str | None = None,
    depends_on_step_ref: str | None = None,
) -> dict:
    return {
        "step_code": step_code,
        "step_type": step_type,
        "step_status": step_status,
        "source_ref": source_ref,
        "depends_on_step_ref": depends_on_step_ref,
    }


def _build_deal_workflow(session: Session, deal_id: str) -> tuple[str, str, WorkflowStatus, list[dict], str | None]:
    deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id, Deal.is_deleted.is_(False)))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")

    latest_execution = session.scalar(
        select(ExecutionCommandSet)
        .where(ExecutionCommandSet.deal_id == deal_id)
        .order_by(ExecutionCommandSet.created_at.desc(), ExecutionCommandSet.id.desc())
        .limit(1)
    )
    latest_execution_record = None
    if latest_execution:
        latest_execution_record = session.scalar(
            select(ExecutionCommandRecord)
            .where(ExecutionCommandRecord.execution_command_set_id == latest_execution.execution_command_set_id)
            .order_by(ExecutionCommandRecord.created_at.desc(), ExecutionCommandRecord.id.desc())
            .limit(1)
        )
    latest_closure = session.scalar(
        select(DealClosureSet)
        .where(DealClosureSet.deal_id == deal_id)
        .order_by(DealClosureSet.created_at.desc(), DealClosureSet.id.desc())
        .limit(1)
    )
    latest_archive_export = session.scalar(
        select(ArchiveExportSet)
        .where(ArchiveExportSet.deal_id == deal_id)
        .order_by(ArchiveExportSet.created_at.desc(), ArchiveExportSet.id.desc())
        .limit(1)
    )
    latest_learning = session.scalar(
        select(LearningAutomationSet)
        .where(
            LearningAutomationSet.scope_type == WorkflowScopeType.DEAL,
            LearningAutomationSet.scope_ref == deal_id,
        )
        .order_by(LearningAutomationSet.created_at.desc(), LearningAutomationSet.id.desc())
        .limit(1)
    )
    latest_outcome = session.scalar(
        select(OutcomeIntakeRecord)
        .join(OutcomeIntakeSet, OutcomeIntakeSet.outcome_intake_set_id == OutcomeIntakeRecord.outcome_intake_set_id)
        .where(OutcomeIntakeSet.deal_id == deal_id)
        .order_by(OutcomeIntakeRecord.effective_at.desc(), OutcomeIntakeRecord.id.desc())
        .limit(1)
    )
    incident_count = int(
        session.scalar(
            select(func.count(IncidentRecord.id))
            .join(IncidentSet, IncidentSet.incident_set_id == IncidentRecord.incident_set_id)
            .where(IncidentSet.deal_id == deal_id)
        )
        or 0
    )
    dashboard_exists = _latest_dashboard_exists(session, WorkflowScopeType.DEAL, deal_id)

    steps: list[dict] = [
        _make_step(
            "CHECK_DEAL_DASHBOARD",
            WorkflowStepType.CHECK,
            WorkflowStepStatus.DONE if dashboard_exists else WorkflowStepStatus.READY,
            source_ref=deal_id,
        )
    ]
    if latest_closure and str(latest_closure.closure_status) == "CLOSED":
        archive_step_status = WorkflowStepStatus.DONE if latest_archive_export else WorkflowStepStatus.READY
        steps.append(
            _make_step(
                "BUILD_ARCHIVE_EXPORT",
                WorkflowStepType.BUILD,
                archive_step_status,
                source_ref=latest_closure.deal_closure_set_id,
                depends_on_step_ref="CHECK_DEAL_DASHBOARD",
            )
        )
        learning_step_status = WorkflowStepStatus.DONE if latest_learning else WorkflowStepStatus.READY
        steps.append(
            _make_step(
                "BUILD_LEARNING_AUTOMATION",
                WorkflowStepType.BUILD,
                learning_step_status,
                source_ref=latest_closure.deal_closure_set_id,
                depends_on_step_ref="BUILD_ARCHIVE_EXPORT",
            )
        )
        close_status = (
            WorkflowStepStatus.DONE
            if latest_archive_export and latest_learning
            else WorkflowStepStatus.PENDING
        )
        steps.append(
            _make_step(
                "CLOSE_OPERATIONAL_LOOP",
                WorkflowStepType.CLOSE,
                close_status,
                source_ref=latest_closure.deal_closure_set_id,
                depends_on_step_ref="BUILD_LEARNING_AUTOMATION",
            )
        )
        workflow_status = WorkflowStatus.COMPLETED if close_status == WorkflowStepStatus.DONE else WorkflowStatus.ACTIVE
        current_phase = "CLOSED_LOOP"
        summary = (
            f"Deal workflow for {deal_id}: closed outcome={getattr(latest_outcome, 'outcome_code', None)}, "
            f"archive_export={'yes' if latest_archive_export else 'no'}, learning={'yes' if latest_learning else 'no'}."
        )
        return summary, current_phase, workflow_status, steps, deal_id

    if latest_execution:
        shipping_set = session.scalar(
            select(ShippingAcceptanceSet)
            .where(ShippingAcceptanceSet.execution_command_set_id == latest_execution.execution_command_set_id)
            .order_by(ShippingAcceptanceSet.created_at.desc(), ShippingAcceptanceSet.id.desc())
            .limit(1)
        )
        shipping_record = None
        if shipping_set:
            shipping_record = session.scalar(
                select(ShippingAcceptanceRecord)
                .where(ShippingAcceptanceRecord.shipping_acceptance_set_id == shipping_set.shipping_acceptance_set_id)
                .order_by(ShippingAcceptanceRecord.created_at.desc(), ShippingAcceptanceRecord.id.desc())
                .limit(1)
            )
        payment_set = session.scalar(
            select(PaymentCollectionSet)
            .where(PaymentCollectionSet.execution_command_set_id == latest_execution.execution_command_set_id)
            .order_by(PaymentCollectionSet.created_at.desc(), PaymentCollectionSet.id.desc())
            .limit(1)
        )
        payment_record = None
        if payment_set:
            payment_record = session.scalar(
                select(PaymentCollectionRecord)
                .where(PaymentCollectionRecord.payment_collection_set_id == payment_set.payment_collection_set_id)
                .order_by(PaymentCollectionRecord.created_at.desc(), PaymentCollectionRecord.id.desc())
                .limit(1)
            )
        shipping_done = shipping_record is not None and str(shipping_record.current_state) in {"ACCEPTED", "COMPLETED"}
        payment_done = payment_record is not None and str(payment_record.collection_state) in {"COLLECTED", "COMPLETED"}
        steps.append(
            _make_step(
                "REVIEW_EXECUTION_STATE",
                WorkflowStepType.REVIEW,
                WorkflowStepStatus.READY,
                source_ref=latest_execution.execution_command_set_id,
                depends_on_step_ref="CHECK_DEAL_DASHBOARD",
            )
        )
        steps.append(
            _make_step(
                "FOLLOW_UP_SHIPPING",
                WorkflowStepType.FOLLOW_UP,
                WorkflowStepStatus.DONE if shipping_done else WorkflowStepStatus.READY,
                source_ref=shipping_set.shipping_acceptance_set_id if shipping_set else latest_execution.execution_command_set_id,
                depends_on_step_ref="REVIEW_EXECUTION_STATE",
            )
        )
        steps.append(
            _make_step(
                "FOLLOW_UP_PAYMENT",
                WorkflowStepType.FOLLOW_UP,
                WorkflowStepStatus.DONE if payment_done else WorkflowStepStatus.READY,
                source_ref=payment_set.payment_collection_set_id if payment_set else latest_execution.execution_command_set_id,
                depends_on_step_ref="FOLLOW_UP_SHIPPING",
            )
        )
        steps.append(
            _make_step(
                "ESCALATE_EXECUTION_INCIDENTS",
                WorkflowStepType.ESCALATE,
                WorkflowStepStatus.READY if incident_count > 0 else WorkflowStepStatus.SKIPPED,
                source_ref=latest_execution.execution_command_set_id,
                depends_on_step_ref="FOLLOW_UP_PAYMENT",
            )
        )
        close_execution_status = (
            WorkflowStepStatus.DONE
            if str(latest_execution.execution_status) == "COMPLETED" and payment_done and incident_count == 0
            else WorkflowStepStatus.PENDING
        )
        steps.append(
            _make_step(
                "CLOSE_EXECUTION_LOOP",
                WorkflowStepType.CLOSE,
                close_execution_status,
                source_ref=latest_execution.execution_command_set_id,
                depends_on_step_ref="ESCALATE_EXECUTION_INCIDENTS",
            )
        )
        workflow_status = WorkflowStatus.COMPLETED if close_execution_status == WorkflowStepStatus.DONE else WorkflowStatus.ACTIVE
        current_phase = str(latest_execution_record.current_phase) if latest_execution_record else str(latest_execution.execution_status)
        summary = (
            f"Deal workflow for {deal_id}: execution_status={latest_execution.execution_status}, "
            f"incidents={incident_count}, shipping_done={shipping_done}, payment_done={payment_done}."
        )
        return summary, current_phase, workflow_status, steps, deal_id

    steps.append(
        _make_step(
            "REVIEW_DEAL_POSITION",
            WorkflowStepType.REVIEW,
            WorkflowStepStatus.READY,
            source_ref=deal_id,
            depends_on_step_ref="CHECK_DEAL_DASHBOARD",
        )
    )
    steps.append(
        _make_step(
            "FOLLOW_UP_NEXT_PHASE",
            WorkflowStepType.FOLLOW_UP,
            WorkflowStepStatus.READY,
            source_ref=deal_id,
            depends_on_step_ref="REVIEW_DEAL_POSITION",
        )
    )
    steps.append(
        _make_step(
            "CLOSE_DEAL_WHEN_READY",
            WorkflowStepType.CLOSE,
            WorkflowStepStatus.PENDING,
            source_ref=deal_id,
            depends_on_step_ref="FOLLOW_UP_NEXT_PHASE",
        )
    )
    summary = f"Deal workflow for {deal_id}: active_status={deal.current_status}, incidents={incident_count}."
    return summary, str(deal.current_status), WorkflowStatus.ACTIVE, steps, deal_id


def _build_execution_workflow(
    session: Session, execution_command_set_id: str
) -> tuple[str, str, WorkflowStatus, list[dict], str | None]:
    execution_set = session.scalar(
        select(ExecutionCommandSet).where(ExecutionCommandSet.execution_command_set_id == execution_command_set_id)
    )
    if not execution_set:
        raise NotFoundError(f"Execution command set '{execution_command_set_id}' was not found")

    latest_execution_record = session.scalar(
        select(ExecutionCommandRecord)
        .where(ExecutionCommandRecord.execution_command_set_id == execution_command_set_id)
        .order_by(ExecutionCommandRecord.created_at.desc(), ExecutionCommandRecord.id.desc())
        .limit(1)
    )
    shipping_set = session.scalar(
        select(ShippingAcceptanceSet)
        .where(ShippingAcceptanceSet.execution_command_set_id == execution_command_set_id)
        .order_by(ShippingAcceptanceSet.created_at.desc(), ShippingAcceptanceSet.id.desc())
        .limit(1)
    )
    shipping_record = None
    if shipping_set:
        shipping_record = session.scalar(
            select(ShippingAcceptanceRecord)
            .where(ShippingAcceptanceRecord.shipping_acceptance_set_id == shipping_set.shipping_acceptance_set_id)
            .order_by(ShippingAcceptanceRecord.created_at.desc(), ShippingAcceptanceRecord.id.desc())
            .limit(1)
        )
    payment_set = session.scalar(
        select(PaymentCollectionSet)
        .where(PaymentCollectionSet.execution_command_set_id == execution_command_set_id)
        .order_by(PaymentCollectionSet.created_at.desc(), PaymentCollectionSet.id.desc())
        .limit(1)
    )
    payment_record = None
    if payment_set:
        payment_record = session.scalar(
            select(PaymentCollectionRecord)
            .where(PaymentCollectionRecord.payment_collection_set_id == payment_set.payment_collection_set_id)
            .order_by(PaymentCollectionRecord.created_at.desc(), PaymentCollectionRecord.id.desc())
            .limit(1)
        )
    incident_count = int(
        session.scalar(
            select(func.count(IncidentRecord.id))
            .join(IncidentSet, IncidentSet.incident_set_id == IncidentRecord.incident_set_id)
            .where(IncidentSet.execution_command_set_id == execution_command_set_id)
        )
        or 0
    )
    shipping_done = shipping_record is not None and str(shipping_record.current_state) in {"ACCEPTED", "COMPLETED"}
    payment_done = payment_record is not None and str(payment_record.collection_state) in {"COLLECTED", "COMPLETED"}
    close_status = (
        WorkflowStepStatus.DONE
        if str(execution_set.execution_status) == "COMPLETED" and payment_done and incident_count == 0
        else WorkflowStepStatus.PENDING
    )
    steps = [
        _make_step("REVIEW_EXECUTION_PHASE", WorkflowStepType.REVIEW, WorkflowStepStatus.READY, source_ref=execution_command_set_id),
        _make_step(
            "FOLLOW_UP_SHIPPING",
            WorkflowStepType.FOLLOW_UP,
            WorkflowStepStatus.DONE if shipping_done else WorkflowStepStatus.READY,
            source_ref=shipping_set.shipping_acceptance_set_id if shipping_set else execution_command_set_id,
            depends_on_step_ref="REVIEW_EXECUTION_PHASE",
        ),
        _make_step(
            "FOLLOW_UP_PAYMENT",
            WorkflowStepType.FOLLOW_UP,
            WorkflowStepStatus.DONE if payment_done else WorkflowStepStatus.READY,
            source_ref=payment_set.payment_collection_set_id if payment_set else execution_command_set_id,
            depends_on_step_ref="FOLLOW_UP_SHIPPING",
        ),
        _make_step(
            "ESCALATE_INCIDENTS",
            WorkflowStepType.ESCALATE,
            WorkflowStepStatus.READY if incident_count > 0 else WorkflowStepStatus.SKIPPED,
            source_ref=execution_command_set_id,
            depends_on_step_ref="FOLLOW_UP_PAYMENT",
        ),
        _make_step(
            "CLOSE_EXECUTION",
            WorkflowStepType.CLOSE,
            close_status,
            source_ref=execution_command_set_id,
            depends_on_step_ref="ESCALATE_INCIDENTS",
        ),
    ]
    status = WorkflowStatus.COMPLETED if close_status == WorkflowStepStatus.DONE else WorkflowStatus.ACTIVE
    phase = str(latest_execution_record.current_phase) if latest_execution_record else str(execution_set.execution_status)
    summary = (
        f"Execution workflow for {execution_command_set_id}: "
        f"status={execution_set.execution_status}, incidents={incident_count}, shipping_done={shipping_done}, payment_done={payment_done}."
    )
    return summary, phase, status, steps, execution_set.deal_id


def _build_pipeline_workflow(session: Session, scope_ref: str) -> tuple[str, str, WorkflowStatus, list[dict], str | None]:
    total_deals = int(session.scalar(select(func.count(Deal.id)).where(Deal.is_deleted.is_(False))) or 0)
    total_execution_sets = int(session.scalar(select(func.count(ExecutionCommandSet.id))) or 0)
    total_incidents = int(session.scalar(select(func.count(IncidentRecord.id))) or 0)
    steps = [
        _make_step("CHECK_PIPELINE_DASHBOARD", WorkflowStepType.CHECK, WorkflowStepStatus.READY, source_ref=scope_ref),
        _make_step(
            "REVIEW_ACTIVE_EXECUTIONS",
            WorkflowStepType.REVIEW,
            WorkflowStepStatus.READY if total_execution_sets > 0 else WorkflowStepStatus.SKIPPED,
            source_ref=scope_ref,
            depends_on_step_ref="CHECK_PIPELINE_DASHBOARD",
        ),
        _make_step(
            "ESCALATE_PIPELINE_BLOCKERS",
            WorkflowStepType.ESCALATE,
            WorkflowStepStatus.READY if total_incidents > 0 else WorkflowStepStatus.SKIPPED,
            source_ref=scope_ref,
            depends_on_step_ref="REVIEW_ACTIVE_EXECUTIONS",
        ),
    ]
    summary = f"Pipeline workflow for {scope_ref}: deals={total_deals}, executions={total_execution_sets}, incidents={total_incidents}."
    return summary, "PIPELINE_OVERVIEW", WorkflowStatus.ACTIVE, steps, None


def _build_portfolio_workflow(
    session: Session, scope_ref: str
) -> tuple[str, str, WorkflowStatus, list[dict], str | None]:
    total_closures = int(session.scalar(select(func.count(DealClosureSet.id))) or 0)
    total_learning_sets = int(session.scalar(select(func.count(LearningAutomationSet.id))) or 0)
    total_exports = int(session.scalar(select(func.count(ArchiveExportSet.id))) or 0)
    steps = [
        _make_step("REVIEW_PORTFOLIO_SIGNALS", WorkflowStepType.REVIEW, WorkflowStepStatus.READY, source_ref=scope_ref),
        _make_step(
            "BUILD_PORTFOLIO_OPTIMIZATION",
            WorkflowStepType.BUILD,
            WorkflowStepStatus.READY if total_learning_sets > 0 else WorkflowStepStatus.BLOCKED,
            source_ref=scope_ref,
            depends_on_step_ref="REVIEW_PORTFOLIO_SIGNALS",
        ),
        _make_step(
            "FOLLOW_UP_PORTFOLIO_PLAYBOOK",
            WorkflowStepType.FOLLOW_UP,
            WorkflowStepStatus.READY if total_closures > 0 else WorkflowStepStatus.BLOCKED,
            source_ref=scope_ref,
            depends_on_step_ref="BUILD_PORTFOLIO_OPTIMIZATION",
        ),
    ]
    summary = f"Portfolio workflow for {scope_ref}: closures={total_closures}, exports={total_exports}, learning_sets={total_learning_sets}."
    return summary, "PORTFOLIO_CONTROL", WorkflowStatus.ACTIVE, steps, None


def build_workflow_run(session: Session, payload: BuildWorkflowRunRequest) -> WorkflowRunSet:
    workflow_set = WorkflowRunSet(
        workflow_run_set_id=next_workflow_run_set_id(session, WorkflowRunSet.workflow_run_set_id),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        workflow_status=WorkflowStatus.BUILT,
    )
    session.add(workflow_set)
    session.flush()
    deal_id_for_event: str | None = payload.scope_ref if payload.scope_type == WorkflowScopeType.DEAL else None
    try:
        if payload.scope_type == WorkflowScopeType.DEAL:
            summary, current_phase, workflow_status, steps, deal_id_for_event = _build_deal_workflow(session, payload.scope_ref)
        elif payload.scope_type == WorkflowScopeType.EXECUTION:
            summary, current_phase, workflow_status, steps, deal_id_for_event = _build_execution_workflow(session, payload.scope_ref)
        elif payload.scope_type == WorkflowScopeType.PIPELINE:
            summary, current_phase, workflow_status, steps, deal_id_for_event = _build_pipeline_workflow(session, payload.scope_ref)
        else:
            summary, current_phase, workflow_status, steps, deal_id_for_event = _build_portfolio_workflow(session, payload.scope_ref)

        workflow_record = WorkflowRunRecord(
            workflow_run_id=next_workflow_run_id(session, WorkflowRunRecord.workflow_run_id),
            workflow_run_set_id=workflow_set.workflow_run_set_id,
            summary_text=summary,
            current_phase=current_phase,
        )
        session.add(workflow_record)
        session.flush()
        for step in steps:
            step_record = WorkflowStepRecord(
                workflow_step_id=next_workflow_step_id(session, WorkflowStepRecord.workflow_step_id),
                workflow_run_id=workflow_record.workflow_run_id,
                **step,
            )
            session.add(step_record)
            session.flush()
            append_event_record(
                session,
                deal_id=deal_id_for_event,
                event_code="workflow_step_recorded",
                source_module_id="M-051",
                severity=EventSeverity.INFO,
                payload_json={
                    "workflow_run_set_id": workflow_set.workflow_run_set_id,
                    "workflow_run_id": workflow_record.workflow_run_id,
                    "workflow_step_id": step_record.workflow_step_id,
                    "step_code": step_record.step_code,
                    "step_status": step_record.step_status,
                },
            )
        workflow_set.workflow_status = workflow_status
        workflow_set.updated_at = utcnow()
        session.add(workflow_set)
        append_event_record(
            session,
            deal_id=deal_id_for_event,
            event_code="workflow_run_built",
            source_module_id="M-051",
            severity=EventSeverity.INFO,
            payload_json={
                "workflow_run_set_id": workflow_set.workflow_run_set_id,
                "workflow_run_id": workflow_record.workflow_run_id,
                "scope_type": str(payload.scope_type),
                "scope_ref": payload.scope_ref,
                "workflow_status": str(workflow_status),
                "step_count": len(steps),
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        failed_set = WorkflowRunSet(
            workflow_run_set_id=workflow_set.workflow_run_set_id,
            scope_type=payload.scope_type,
            scope_ref=payload.scope_ref,
            workflow_status=WorkflowStatus.FAILED,
        )
        session.add(failed_set)
        append_event_record(
            session,
            deal_id=deal_id_for_event,
            event_code="workflow_run_failed",
            source_module_id="M-051",
            severity=EventSeverity.HIGH,
            payload_json={"workflow_run_set_id": workflow_set.workflow_run_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(workflow_set)
    return workflow_set


def get_workflow_run_set(
    session: Session,
    workflow_run_set_id: str,
) -> tuple[WorkflowRunSet, list[tuple[WorkflowRunRecord, list[WorkflowStepRecord]]]]:
    workflow_set = _get_set(session, workflow_run_set_id)
    records = _get_records(session, workflow_run_set_id)
    return workflow_set, [(record, _get_steps(session, record.workflow_run_id)) for record in records]


def list_workflow_run_sets(
    session: Session,
    *,
    scope_type: WorkflowScopeType | None = None,
    scope_ref: str | None = None,
) -> list[tuple[WorkflowRunSet, list[tuple[WorkflowRunRecord, list[WorkflowStepRecord]]]]]:
    query = select(WorkflowRunSet).order_by(WorkflowRunSet.created_at.desc(), WorkflowRunSet.id.desc())
    if scope_type:
        query = query.where(WorkflowRunSet.scope_type == scope_type)
    if scope_ref:
        query = query.where(WorkflowRunSet.scope_ref == scope_ref)
    sets = list(session.scalars(query))
    return [get_workflow_run_set(session, item.workflow_run_set_id) for item in sets]


def get_workflow_run_record(
    session: Session, workflow_run_id: str
) -> tuple[WorkflowRunRecord, list[WorkflowStepRecord]]:
    record = _get_record(session, workflow_run_id)
    return record, _get_steps(session, workflow_run_id)
