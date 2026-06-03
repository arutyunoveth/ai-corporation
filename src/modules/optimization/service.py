from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.archive_export.models import ArchiveExportSet
from src.modules.dashboard_snapshots.models import DashboardMetricRecord, DashboardSnapshotRecord, DashboardSnapshotSet
from src.modules.deal_registry.models import Deal
from src.modules.event_log.service import append_event_record
from src.modules.kpi_learning.models import KPILearningRecord, KPILearningSet
from src.modules.learning_automation.models import (
    LearningAutomationRecord,
    LearningAutomationSet,
    LearningRecommendationRecord,
)
from src.modules.optimization.models import (
    OptimizationRecommendationRecord,
    OptimizationRecommendationSet,
    OptimizationSignalRecord,
)
from src.modules.optimization.schemas import BuildOptimizationRequest
from src.modules.workflow_runs.models import WorkflowRunRecord, WorkflowRunSet
from src.shared.db.base import utcnow
from src.shared.enums import (
    DashboardScopeType,
    EventSeverity,
    OptimizationRecommendationType,
    OptimizationScopeType,
    OptimizationStatus,
    WorkflowScopeType,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_optimization_recommendation_id, next_optimization_recommendation_set_id


def _get_set(session: Session, optimization_recommendation_set_id: str) -> OptimizationRecommendationSet:
    record = session.scalar(
        select(OptimizationRecommendationSet).where(
            OptimizationRecommendationSet.optimization_recommendation_set_id == optimization_recommendation_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Optimization recommendation set '{optimization_recommendation_set_id}' was not found")
    return record


def _get_record(session: Session, optimization_recommendation_id: str) -> OptimizationRecommendationRecord:
    record = session.scalar(
        select(OptimizationRecommendationRecord).where(
            OptimizationRecommendationRecord.optimization_recommendation_id == optimization_recommendation_id
        )
    )
    if not record:
        raise NotFoundError(f"Optimization recommendation record '{optimization_recommendation_id}' was not found")
    return record


def _get_records(session: Session, optimization_recommendation_set_id: str) -> list[OptimizationRecommendationRecord]:
    return list(
        session.scalars(
            select(OptimizationRecommendationRecord)
            .where(
                OptimizationRecommendationRecord.optimization_recommendation_set_id
                == optimization_recommendation_set_id
            )
            .order_by(OptimizationRecommendationRecord.created_at.asc(), OptimizationRecommendationRecord.id.asc())
        )
    )


def _get_signals(session: Session, optimization_recommendation_id: str) -> list[OptimizationSignalRecord]:
    return list(
        session.scalars(
            select(OptimizationSignalRecord)
            .where(OptimizationSignalRecord.optimization_recommendation_id == optimization_recommendation_id)
            .order_by(OptimizationSignalRecord.created_at.asc(), OptimizationSignalRecord.id.asc())
        )
    )


def _latest_dashboard_metrics(
    session: Session, scope_type: DashboardScopeType, scope_ref: str
) -> tuple[DashboardSnapshotSet | None, DashboardSnapshotRecord | None, dict[str, DashboardMetricRecord]]:
    dashboard_set = session.scalar(
        select(DashboardSnapshotSet)
        .where(DashboardSnapshotSet.scope_type == scope_type, DashboardSnapshotSet.scope_ref == scope_ref)
        .order_by(DashboardSnapshotSet.created_at.desc(), DashboardSnapshotSet.id.desc())
        .limit(1)
    )
    if not dashboard_set:
        return None, None, {}
    dashboard_record = session.scalar(
        select(DashboardSnapshotRecord)
        .where(DashboardSnapshotRecord.dashboard_snapshot_set_id == dashboard_set.dashboard_snapshot_set_id)
        .order_by(DashboardSnapshotRecord.created_at.desc(), DashboardSnapshotRecord.id.desc())
        .limit(1)
    )
    if not dashboard_record:
        return dashboard_set, None, {}
    metrics = list(
        session.scalars(
            select(DashboardMetricRecord).where(
                DashboardMetricRecord.dashboard_snapshot_id == dashboard_record.dashboard_snapshot_id
            )
        )
    )
    return dashboard_set, dashboard_record, {metric.metric_code: metric for metric in metrics}


def _latest_learning_context(
    session: Session, scope_type: WorkflowScopeType, scope_ref: str
) -> tuple[LearningAutomationSet | None, LearningAutomationRecord | None, list[LearningRecommendationRecord]]:
    learning_set = session.scalar(
        select(LearningAutomationSet)
        .where(LearningAutomationSet.scope_type == scope_type, LearningAutomationSet.scope_ref == scope_ref)
        .order_by(LearningAutomationSet.created_at.desc(), LearningAutomationSet.id.desc())
        .limit(1)
    )
    if not learning_set:
        return None, None, []
    learning_record = session.scalar(
        select(LearningAutomationRecord)
        .where(LearningAutomationRecord.learning_automation_set_id == learning_set.learning_automation_set_id)
        .order_by(LearningAutomationRecord.created_at.desc(), LearningAutomationRecord.id.desc())
        .limit(1)
    )
    recommendations: list[LearningRecommendationRecord] = []
    if learning_record:
        recommendations = list(
            session.scalars(
                select(LearningRecommendationRecord)
                .where(LearningRecommendationRecord.learning_automation_id == learning_record.learning_automation_id)
                .order_by(LearningRecommendationRecord.created_at.asc(), LearningRecommendationRecord.id.asc())
            )
        )
    return learning_set, learning_record, recommendations


def _latest_workflow_set(
    session: Session, scope_type: WorkflowScopeType, scope_ref: str
) -> WorkflowRunSet | None:
    return session.scalar(
        select(WorkflowRunSet)
        .where(WorkflowRunSet.scope_type == scope_type, WorkflowRunSet.scope_ref == scope_ref)
        .order_by(WorkflowRunSet.created_at.desc(), WorkflowRunSet.id.desc())
        .limit(1)
    )


def _latest_workflow_record(session: Session, workflow_run_set_id: str) -> WorkflowRunRecord | None:
    return session.scalar(
        select(WorkflowRunRecord)
        .where(WorkflowRunRecord.workflow_run_set_id == workflow_run_set_id)
        .order_by(WorkflowRunRecord.created_at.desc(), WorkflowRunRecord.id.desc())
        .limit(1)
    )


def _build_deal_optimization(
    session: Session, deal_id: str
) -> tuple[str, list[dict], list[dict], str | None]:
    deal = session.scalar(select(Deal).where(Deal.deal_id == deal_id, Deal.is_deleted.is_(False)))
    if not deal:
        raise NotFoundError(f"Deal '{deal_id}' was not found")

    dashboard_set, dashboard_record, dashboard_metrics = _latest_dashboard_metrics(session, DashboardScopeType.DEAL, deal_id)
    learning_set, _learning_record, learning_recommendations = _latest_learning_context(session, WorkflowScopeType.DEAL, deal_id)
    if not learning_set:
        raise ValidationError("Deal optimization requires persisted learning automation")
    if not dashboard_set or not dashboard_record:
        raise ValidationError("Deal optimization requires persisted dashboard snapshot")

    latest_kpi_record = session.scalar(
        select(KPILearningRecord)
        .join(KPILearningSet, KPILearningSet.kpi_learning_set_id == KPILearningRecord.kpi_learning_set_id)
        .where(KPILearningSet.deal_id == deal_id)
        .order_by(KPILearningRecord.created_at.desc(), KPILearningRecord.id.desc())
        .limit(1)
    )
    latest_archive_export = session.scalar(
        select(ArchiveExportSet)
        .where(ArchiveExportSet.deal_id == deal_id)
        .order_by(ArchiveExportSet.created_at.desc(), ArchiveExportSet.id.desc())
        .limit(1)
    )
    latest_workflow_set = _latest_workflow_set(session, WorkflowScopeType.DEAL, deal_id)
    latest_workflow_record = (
        _latest_workflow_record(session, latest_workflow_set.workflow_run_set_id) if latest_workflow_set else None
    )

    incident_metric = dashboard_metrics.get("incident_count")
    incident_count = (
        latest_kpi_record.incident_count
        if latest_kpi_record
        else int(incident_metric.metric_value_numeric or 0) if incident_metric else 0
    )
    margin_estimate = latest_kpi_record.margin_estimate if latest_kpi_record else None
    cycle_time_days = latest_kpi_record.cycle_time_days if latest_kpi_record else None
    supplier_count = latest_kpi_record.supplier_count if latest_kpi_record else None

    signals = [
        {"signal_code": "deal_status", "signal_value_text": str(deal.current_status), "source_ref": deal_id},
        {
            "signal_code": "workflow_status",
            "signal_value_text": str(latest_workflow_set.workflow_status) if latest_workflow_set else "UNAVAILABLE",
            "source_ref": latest_workflow_set.workflow_run_set_id if latest_workflow_set else None,
        },
        {
            "signal_code": "learning_recommendation_count",
            "signal_value_text": str(len(learning_recommendations)),
            "source_ref": learning_set.learning_automation_set_id,
        },
        {
            "signal_code": "archive_export_status",
            "signal_value_text": str(latest_archive_export.export_status) if latest_archive_export else "MISSING",
            "source_ref": latest_archive_export.archive_export_set_id if latest_archive_export else None,
        },
        {
            "signal_code": "incident_count",
            "signal_value_text": str(incident_count),
            "source_ref": latest_kpi_record.kpi_learning_id if latest_kpi_record else dashboard_record.dashboard_snapshot_id,
        },
    ]
    if margin_estimate is not None:
        signals.append(
            {
                "signal_code": "margin_estimate",
                "signal_value_text": f"{margin_estimate:.2f}",
                "source_ref": latest_kpi_record.kpi_learning_id if latest_kpi_record else None,
            }
        )
    if cycle_time_days is not None:
        signals.append(
            {
                "signal_code": "cycle_time_days",
                "signal_value_text": f"{cycle_time_days:.1f}",
                "source_ref": latest_kpi_record.kpi_learning_id if latest_kpi_record else None,
            }
        )

    recommendations: list[dict] = []
    if incident_count > 0:
        recommendations.append(
            {
                "recommendation_code": "DEAL_REDUCE_EXECUTION_INCIDENTS",
                "recommendation_type": OptimizationRecommendationType.RISK_REDUCTION,
                "recommendation_text": "Сократить execution friction через обязательный incident follow-up workflow до закрытия сделки.",
                "confidence_score": 0.84,
            }
        )
    if margin_estimate is not None and margin_estimate <= 0:
        recommendations.append(
            {
                "recommendation_code": "DEAL_MARGIN_GUARDRAIL",
                "recommendation_type": OptimizationRecommendationType.MARGIN,
                "recommendation_text": "Ввести margin guardrail до следующего аналогичного bid decision.",
                "confidence_score": 0.88,
            }
        )
    if cycle_time_days is not None and cycle_time_days > 30:
        recommendations.append(
            {
                "recommendation_code": "DEAL_CYCLE_TIME_REDUCTION",
                "recommendation_type": OptimizationRecommendationType.CYCLE_TIME,
                "recommendation_text": "Сократить cycle time через ранний orchestration checkpoint и pre-built handover checklist.",
                "confidence_score": 0.74,
            }
        )
    if supplier_count is not None and supplier_count < 2:
        recommendations.append(
            {
                "recommendation_code": "DEAL_SUPPLIER_COVERAGE",
                "recommendation_type": OptimizationRecommendationType.SUPPLIER_STRATEGY,
                "recommendation_text": "Расширять supplier coverage заранее, чтобы убрать single-path dependence в коммерческом контуре.",
                "confidence_score": 0.76,
            }
        )
    if not latest_archive_export or str(latest_archive_export.export_status) != "EXPORTED":
        recommendations.append(
            {
                "recommendation_code": "DEAL_EXPORT_DISCIPLINE",
                "recommendation_type": OptimizationRecommendationType.PROCESS_DISCIPLINE,
                "recommendation_text": "Фиксировать archive export как обязательный close-out deliverable перед переводом кейса в исторический контур.",
                "confidence_score": 0.67,
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "recommendation_code": "DEAL_MONITORING_ONLY",
                "recommendation_type": OptimizationRecommendationType.OTHER,
                "recommendation_text": "Оставить сделку в monitoring contour без дополнительных optimization actions.",
                "confidence_score": 0.55,
            }
        )

    summary = (
        f"Deal optimization for {deal_id}: learning={len(learning_recommendations)}, "
        f"workflow_phase={getattr(latest_workflow_record, 'current_phase', 'N/A')}, recommendations={len(recommendations)}."
    )
    return summary, recommendations, signals, deal_id


def _build_portfolio_optimization(
    session: Session, scope_ref: str
) -> tuple[str, list[dict], list[dict], str | None]:
    total_learning_sets = int(
        session.scalar(
            select(func.count(LearningAutomationSet.id)).where(
                LearningAutomationSet.scope_type == WorkflowScopeType.PORTFOLIO,
                LearningAutomationSet.scope_ref == scope_ref,
            )
        )
        or 0
    )
    total_dashboards = int(
        session.scalar(
            select(func.count(DashboardSnapshotSet.id)).where(
                DashboardSnapshotSet.scope_type == DashboardScopeType.GLOBAL,
                DashboardSnapshotSet.scope_ref == scope_ref,
            )
        )
        or 0
    )
    avg_margin = session.scalar(select(func.avg(KPILearningRecord.margin_estimate))) or 0.0
    avg_cycle_time = session.scalar(select(func.avg(KPILearningRecord.cycle_time_days))) or 0.0
    total_incidents = int(session.scalar(select(func.sum(KPILearningRecord.incident_count))) or 0)
    signals = [
        {"signal_code": "portfolio_learning_sets", "signal_value_text": str(total_learning_sets), "source_ref": scope_ref},
        {"signal_code": "global_dashboard_sets", "signal_value_text": str(total_dashboards), "source_ref": scope_ref},
        {"signal_code": "avg_margin_estimate", "signal_value_text": f"{avg_margin:.2f}", "source_ref": scope_ref},
        {"signal_code": "avg_cycle_time_days", "signal_value_text": f"{avg_cycle_time:.2f}", "source_ref": scope_ref},
        {"signal_code": "portfolio_incident_total", "signal_value_text": str(total_incidents), "source_ref": scope_ref},
    ]
    recommendations: list[dict] = []
    if avg_cycle_time > 30:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_CYCLE_TIME_POLICY",
                "recommendation_type": OptimizationRecommendationType.CYCLE_TIME,
                "recommendation_text": "Ввести портфельный SLA на прохождение orchestration checkpoints для длинных сделок.",
                "confidence_score": 0.73,
            }
        )
    if avg_margin <= 0:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_MARGIN_POLICY",
                "recommendation_type": OptimizationRecommendationType.MARGIN,
                "recommendation_text": "Поднять portfolio-level guardrail review для сделок с отрицательной или нулевой маржей.",
                "confidence_score": 0.82,
            }
        )
    if total_incidents > 0:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_RISK_PLAYBOOK",
                "recommendation_type": OptimizationRecommendationType.RISK_REDUCTION,
                "recommendation_text": "Свернуть recurring execution incidents в единый risk-prevention playbook.",
                "confidence_score": 0.79,
            }
        )
    if not recommendations:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_OBSERVE_ONLY",
                "recommendation_type": OptimizationRecommendationType.OTHER,
                "recommendation_text": "Сохранить portfolio monitoring без новых optimization interventions.",
                "confidence_score": 0.54,
            }
        )
    summary = (
        f"Portfolio optimization for {scope_ref}: dashboards={total_dashboards}, "
        f"learning_sets={total_learning_sets}, recommendations={len(recommendations)}."
    )
    return summary, recommendations, signals, None


def _build_process_optimization(
    session: Session, scope_ref: str
) -> tuple[str, list[dict], list[dict], str | None]:
    latest_workflow_set = _latest_workflow_set(session, WorkflowScopeType.PIPELINE, scope_ref)
    total_exports = int(session.scalar(select(func.count(ArchiveExportSet.id))) or 0)
    total_workflows = int(session.scalar(select(func.count(WorkflowRunSet.id))) or 0)
    signals = [
        {
            "signal_code": "latest_pipeline_workflow_status",
            "signal_value_text": str(latest_workflow_set.workflow_status) if latest_workflow_set else "MISSING",
            "source_ref": latest_workflow_set.workflow_run_set_id if latest_workflow_set else scope_ref,
        },
        {"signal_code": "total_archive_exports", "signal_value_text": str(total_exports), "source_ref": scope_ref},
        {"signal_code": "total_workflow_runs", "signal_value_text": str(total_workflows), "source_ref": scope_ref},
    ]
    recommendations = [
        {
            "recommendation_code": "PROCESS_DISCIPLINE_CHECKPOINTS",
            "recommendation_type": OptimizationRecommendationType.PROCESS_DISCIPLINE,
            "recommendation_text": "Стандартизировать orchestration checkpoints между pipeline review и archive handover.",
            "confidence_score": 0.69,
        }
    ]
    summary = f"Process optimization for {scope_ref}: exports={total_exports}, workflows={total_workflows}."
    return summary, recommendations, signals, None


def _build_supplier_optimization(
    session: Session, scope_ref: str
) -> tuple[str, list[dict], list[dict], str | None]:
    from src.modules.supplier_registry.models import SupplierProfile
    from src.modules.supplier_verification.models import SupplierVerificationSet

    supplier = session.scalar(select(SupplierProfile).where(SupplierProfile.supplier_id == scope_ref))
    if not supplier:
        raise NotFoundError(f"Supplier '{scope_ref}' was not found")
    verification_count = int(
        session.scalar(
            select(func.count(SupplierVerificationSet.id)).where(SupplierVerificationSet.supplier_id == scope_ref)
        )
        or 0
    )
    signals = [
        {"signal_code": "supplier_status", "signal_value_text": str(supplier.supplier_status), "source_ref": scope_ref},
        {"signal_code": "verification_count", "signal_value_text": str(verification_count), "source_ref": scope_ref},
    ]
    recommendations = [
        {
            "recommendation_code": "SUPPLIER_VERIFICATION_DISCIPLINE",
            "recommendation_type": OptimizationRecommendationType.SUPPLIER_STRATEGY,
            "recommendation_text": "Поддерживать регулярный supplier verification cadence перед критичными закупками.",
            "confidence_score": 0.71,
        }
    ]
    summary = f"Supplier optimization for {scope_ref}: verifications={verification_count}."
    return summary, recommendations, signals, None


def build_optimization(session: Session, payload: BuildOptimizationRequest) -> OptimizationRecommendationSet:
    optimization_set = OptimizationRecommendationSet(
        optimization_recommendation_set_id=next_optimization_recommendation_set_id(
            session, OptimizationRecommendationSet.optimization_recommendation_set_id
        ),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        optimization_status=OptimizationStatus.BUILT,
    )
    session.add(optimization_set)
    session.flush()
    deal_id_for_event: str | None = payload.scope_ref if payload.scope_type == OptimizationScopeType.DEAL else None
    try:
        if payload.scope_type == OptimizationScopeType.DEAL:
            summary, recommendations, signals, deal_id_for_event = _build_deal_optimization(session, payload.scope_ref)
        elif payload.scope_type == OptimizationScopeType.PORTFOLIO:
            summary, recommendations, signals, deal_id_for_event = _build_portfolio_optimization(session, payload.scope_ref)
        elif payload.scope_type == OptimizationScopeType.PROCESS:
            summary, recommendations, signals, deal_id_for_event = _build_process_optimization(session, payload.scope_ref)
        else:
            summary, recommendations, signals, deal_id_for_event = _build_supplier_optimization(session, payload.scope_ref)

        summary_record = OptimizationRecommendationRecord(
            optimization_recommendation_id=next_optimization_recommendation_id(
                session, OptimizationRecommendationRecord.optimization_recommendation_id
            ),
            optimization_recommendation_set_id=optimization_set.optimization_recommendation_set_id,
            recommendation_code="OPTIMIZATION_SUMMARY",
            recommendation_type=OptimizationRecommendationType.OTHER,
            recommendation_text=summary,
            confidence_score=None,
        )
        session.add(summary_record)
        session.flush()
        for signal in signals:
            signal_record = OptimizationSignalRecord(
                optimization_recommendation_id=summary_record.optimization_recommendation_id,
                **signal,
            )
            session.add(signal_record)
            session.flush()
            append_event_record(
                session,
                deal_id=deal_id_for_event,
                event_code="optimization_signal_recorded",
                source_module_id="M-052",
                severity=EventSeverity.INFO,
                payload_json={
                    "optimization_recommendation_set_id": optimization_set.optimization_recommendation_set_id,
                    "optimization_recommendation_id": summary_record.optimization_recommendation_id,
                    "signal_code": signal_record.signal_code,
                },
            )
        for recommendation in recommendations:
            recommendation_record = OptimizationRecommendationRecord(
                optimization_recommendation_id=next_optimization_recommendation_id(
                    session, OptimizationRecommendationRecord.optimization_recommendation_id
                ),
                optimization_recommendation_set_id=optimization_set.optimization_recommendation_set_id,
                **recommendation,
            )
            session.add(recommendation_record)
            session.flush()
        optimization_set.updated_at = utcnow()
        session.add(optimization_set)
        append_event_record(
            session,
            deal_id=deal_id_for_event,
            event_code="optimization_recommendations_built",
            source_module_id="M-052",
            severity=EventSeverity.INFO,
            payload_json={
                "optimization_recommendation_set_id": optimization_set.optimization_recommendation_set_id,
                "scope_type": str(payload.scope_type),
                "scope_ref": payload.scope_ref,
                "recommendation_count": len(recommendations),
                "signal_count": len(signals),
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        failed_set = OptimizationRecommendationSet(
            optimization_recommendation_set_id=optimization_set.optimization_recommendation_set_id,
            scope_type=payload.scope_type,
            scope_ref=payload.scope_ref,
            optimization_status=OptimizationStatus.FAILED,
        )
        session.add(failed_set)
        append_event_record(
            session,
            deal_id=deal_id_for_event,
            event_code="optimization_recommendations_failed",
            source_module_id="M-052",
            severity=EventSeverity.HIGH,
            payload_json={
                "optimization_recommendation_set_id": optimization_set.optimization_recommendation_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise
    session.refresh(optimization_set)
    return optimization_set


def get_optimization_set(
    session: Session, optimization_recommendation_set_id: str
) -> tuple[
    OptimizationRecommendationSet,
    list[tuple[OptimizationRecommendationRecord, list[OptimizationSignalRecord]]],
]:
    optimization_set = _get_set(session, optimization_recommendation_set_id)
    records = _get_records(session, optimization_recommendation_set_id)
    return optimization_set, [(record, _get_signals(session, record.optimization_recommendation_id)) for record in records]


def list_optimization_sets(
    session: Session,
    *,
    scope_type: OptimizationScopeType | None = None,
    scope_ref: str | None = None,
) -> list[tuple[OptimizationRecommendationSet, list[tuple[OptimizationRecommendationRecord, list[OptimizationSignalRecord]]]]]:
    query = select(OptimizationRecommendationSet).order_by(
        OptimizationRecommendationSet.created_at.desc(), OptimizationRecommendationSet.id.desc()
    )
    if scope_type:
        query = query.where(OptimizationRecommendationSet.scope_type == scope_type)
    if scope_ref:
        query = query.where(OptimizationRecommendationSet.scope_ref == scope_ref)
    sets = list(session.scalars(query))
    return [get_optimization_set(session, item.optimization_recommendation_set_id) for item in sets]


def get_optimization_record(
    session: Session, optimization_recommendation_id: str
) -> tuple[OptimizationRecommendationRecord, list[OptimizationSignalRecord]]:
    record = _get_record(session, optimization_recommendation_id)
    return record, _get_signals(session, optimization_recommendation_id)
