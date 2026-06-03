from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.deal_closure.models import DealClosureSet
from src.modules.event_log.service import append_event_record
from src.modules.kpi_learning.models import KPILearningRecord, KPILearningSet, LearningNoteRecord
from src.modules.learning_automation.models import (
    LearningAutomationRecord,
    LearningAutomationSet,
    LearningRecommendationRecord,
)
from src.modules.learning_automation.schemas import BuildLearningAutomationRequest
from src.shared.db.base import utcnow
from src.shared.enums import (
    DealClosureStatus,
    EventSeverity,
    LearningAutomationScopeType,
    LearningAutomationStatus,
    LearningRecommendationType,
    LearningNoteType,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_learning_automation_id, next_learning_automation_set_id
from src.shared.validation import require_same_reference


def _get_set(session: Session, learning_automation_set_id: str) -> LearningAutomationSet:
    record = session.scalar(
        select(LearningAutomationSet).where(
            LearningAutomationSet.learning_automation_set_id == learning_automation_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Learning automation set '{learning_automation_set_id}' was not found")
    return record


def _get_record(session: Session, learning_automation_id: str) -> LearningAutomationRecord:
    record = session.scalar(
        select(LearningAutomationRecord).where(
            LearningAutomationRecord.learning_automation_id == learning_automation_id
        )
    )
    if not record:
        raise NotFoundError(f"Learning automation record '{learning_automation_id}' was not found")
    return record


def _get_records(session: Session, learning_automation_set_id: str) -> list[LearningAutomationRecord]:
    return list(
        session.scalars(
            select(LearningAutomationRecord)
            .where(LearningAutomationRecord.learning_automation_set_id == learning_automation_set_id)
            .order_by(LearningAutomationRecord.created_at.asc(), LearningAutomationRecord.id.asc())
        )
    )


def _get_recommendations(session: Session, learning_automation_id: str) -> list[LearningRecommendationRecord]:
    return list(
        session.scalars(
            select(LearningRecommendationRecord)
            .where(LearningRecommendationRecord.learning_automation_id == learning_automation_id)
            .order_by(LearningRecommendationRecord.created_at.asc(), LearningRecommendationRecord.id.asc())
        )
    )


def _build_deal_recommendations(
    session: Session,
    *,
    scope_ref: str,
    deal_closure_set_id: str,
    kpi_learning_set_id: str,
) -> tuple[str, list[dict]]:
    closure_set = session.scalar(
        select(DealClosureSet).where(DealClosureSet.deal_closure_set_id == deal_closure_set_id)
    )
    if not closure_set:
        raise NotFoundError(f"Deal closure set '{deal_closure_set_id}' was not found")
    require_same_reference(scope_ref, closure_set.deal_id, "scope_ref")
    if str(closure_set.closure_status) != str(DealClosureStatus.CLOSED):
        raise ValidationError("Deal learning automation requires a CLOSED deal closure set")

    kpi_set = session.scalar(
        select(KPILearningSet).where(KPILearningSet.kpi_learning_set_id == kpi_learning_set_id)
    )
    if not kpi_set:
        raise NotFoundError(f"KPI learning set '{kpi_learning_set_id}' was not found")
    require_same_reference(scope_ref, kpi_set.deal_id, "scope_ref")

    kpi_record = session.scalar(
        select(KPILearningRecord)
        .where(KPILearningRecord.kpi_learning_set_id == kpi_set.kpi_learning_set_id)
        .order_by(KPILearningRecord.created_at.desc(), KPILearningRecord.id.desc())
        .limit(1)
    )
    if not kpi_record:
        raise ValidationError("Learning automation requires a persisted KPI record")
    notes = list(
        session.scalars(
            select(LearningNoteRecord)
            .where(LearningNoteRecord.kpi_learning_id == kpi_record.kpi_learning_id)
            .order_by(LearningNoteRecord.created_at.asc(), LearningNoteRecord.id.asc())
        )
    )

    recommendations: list[dict] = []
    if kpi_record.incident_count > 0:
        recommendations.append(
            {
                "recommendation_code": "DEAL_INCIDENT_REVIEW",
                "recommendation_type": LearningRecommendationType.RISK_PREVENTION,
                "recommendation_text": "Собрать pre-mortem checklist для предотвращения повторения execution incidents.",
                "source_ref": kpi_set.kpi_learning_set_id,
            }
        )
    if kpi_record.margin_estimate is not None and kpi_record.margin_estimate <= 0:
        recommendations.append(
            {
                "recommendation_code": "DEAL_MARGIN_DISCIPLINE",
                "recommendation_type": LearningRecommendationType.PRICING_DISCIPLINE,
                "recommendation_text": "Усилить cost guardrails перед следующими ставками со схожим профилем сделки.",
                "source_ref": kpi_set.kpi_learning_set_id,
            }
        )
    if kpi_record.supplier_count < 2:
        recommendations.append(
            {
                "recommendation_code": "DEAL_SUPPLIER_DEPTH",
                "recommendation_type": LearningRecommendationType.SUPPLIER_STRATEGY,
                "recommendation_text": "Расширять shortlist заранее, чтобы не зависеть от одного-двух поставщиков.",
                "source_ref": kpi_set.kpi_learning_set_id,
            }
        )
    for note in notes:
        if note.note_type == LearningNoteType.PROCESS_GAP:
            recommendations.append(
                {
                    "recommendation_code": f"NOTE_{note.learning_note_id}_CHECKLIST",
                    "recommendation_type": LearningRecommendationType.CHECKLIST,
                    "recommendation_text": note.note_text,
                    "source_ref": note.learning_note_id,
                }
            )
        elif note.note_type == LearningNoteType.WHAT_FAILED:
            recommendations.append(
                {
                    "recommendation_code": f"NOTE_{note.learning_note_id}_PLAYBOOK",
                    "recommendation_type": LearningRecommendationType.PLAYBOOK,
                    "recommendation_text": note.note_text,
                    "source_ref": note.learning_note_id,
                }
            )
        elif note.note_type == LearningNoteType.SUPPLIER_LEARNING:
            recommendations.append(
                {
                    "recommendation_code": f"NOTE_{note.learning_note_id}_SUPPLIER",
                    "recommendation_type": LearningRecommendationType.SUPPLIER_STRATEGY,
                    "recommendation_text": note.note_text,
                    "source_ref": note.learning_note_id,
                }
            )
    summary = (
        f"Deal learning automation for {scope_ref}: "
        f"incidents={kpi_record.incident_count}, suppliers={kpi_record.supplier_count}, notes={len(notes)}."
    )
    return summary, recommendations


def _build_portfolio_recommendations(session: Session, scope_ref: str) -> tuple[str, list[dict]]:
    total_kpi_sets = int(session.scalar(select(func.count(KPILearningSet.id))) or 0)
    avg_incidents = session.scalar(select(func.avg(KPILearningRecord.incident_count))) or 0.0
    avg_suppliers = session.scalar(select(func.avg(KPILearningRecord.supplier_count))) or 0.0
    negative_margin_count = int(
        session.scalar(
            select(func.count(KPILearningRecord.id)).where(KPILearningRecord.margin_estimate.is_not(None), KPILearningRecord.margin_estimate <= 0)
        )
        or 0
    )
    note_count = int(session.scalar(select(func.count(LearningNoteRecord.id))) or 0)
    recommendations: list[dict] = []
    if avg_incidents > 0:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_RISK_PREVENTION",
                "recommendation_type": LearningRecommendationType.RISK_PREVENTION,
                "recommendation_text": "Сформировать стандартный prevention checklist для execution-phase incidents на уровне портфеля.",
                "source_ref": scope_ref,
            }
        )
    if negative_margin_count > 0:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_PRICING_DISCIPLINE",
                "recommendation_type": LearningRecommendationType.PRICING_DISCIPLINE,
                "recommendation_text": "Ввести портфельный review для сделок с риском нулевой или отрицательной маржи.",
                "source_ref": scope_ref,
            }
        )
    if avg_suppliers < 2:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_SUPPLIER_STRATEGY",
                "recommendation_type": LearningRecommendationType.SUPPLIER_STRATEGY,
                "recommendation_text": "Наращивать supplier coverage по типовым категориям закупок на уровне портфеля.",
                "source_ref": scope_ref,
            }
        )
    if note_count > 0:
        recommendations.append(
            {
                "recommendation_code": "PORTFOLIO_PLAYBOOK_ROLLOUT",
                "recommendation_type": LearningRecommendationType.PLAYBOOK,
                "recommendation_text": "Свернуть накопленные learning notes в повторяемый operating playbook для новых сделок.",
                "source_ref": scope_ref,
            }
        )
    summary = (
        f"Portfolio learning automation for {scope_ref}: "
        f"kpi_sets={total_kpi_sets}, avg_incidents={avg_incidents:.2f}, notes={note_count}."
    )
    return summary, recommendations


def build_learning_automation(session: Session, payload: BuildLearningAutomationRequest) -> LearningAutomationSet:
    automation_set = LearningAutomationSet(
        learning_automation_set_id=next_learning_automation_set_id(
            session, LearningAutomationSet.learning_automation_set_id
        ),
        scope_type=payload.scope_type,
        scope_ref=payload.scope_ref,
        automation_status=LearningAutomationStatus.BUILT,
    )
    session.add(automation_set)
    session.flush()
    try:
        if payload.scope_type == LearningAutomationScopeType.DEAL:
            if not payload.deal_closure_set_id or not payload.kpi_learning_set_id:
                raise ValidationError("Deal learning automation requires deal_closure_set_id and kpi_learning_set_id")
            summary_text, recommendations = _build_deal_recommendations(
                session,
                scope_ref=payload.scope_ref,
                deal_closure_set_id=payload.deal_closure_set_id,
                kpi_learning_set_id=payload.kpi_learning_set_id,
            )
        else:
            summary_text, recommendations = _build_portfolio_recommendations(session, payload.scope_ref)

        record = LearningAutomationRecord(
            learning_automation_id=next_learning_automation_id(
                session, LearningAutomationRecord.learning_automation_id
            ),
            learning_automation_set_id=automation_set.learning_automation_set_id,
            summary_text=summary_text,
        )
        session.add(record)
        session.flush()
        for recommendation in recommendations:
            session.add(LearningRecommendationRecord(learning_automation_id=record.learning_automation_id, **recommendation))
            session.flush()
            append_event_record(
                session,
                deal_id=payload.scope_ref if payload.scope_type == LearningAutomationScopeType.DEAL else None,
                event_code="learning_recommendation_recorded",
                source_module_id="M-050",
                severity=EventSeverity.INFO,
                payload_json={
                    "learning_automation_set_id": automation_set.learning_automation_set_id,
                    "learning_automation_id": record.learning_automation_id,
                    "recommendation_code": recommendation["recommendation_code"],
                    "recommendation_type": str(recommendation["recommendation_type"]),
                },
            )
        automation_set.updated_at = utcnow()
        session.add(automation_set)
        append_event_record(
            session,
            deal_id=payload.scope_ref if payload.scope_type == LearningAutomationScopeType.DEAL else None,
            event_code="learning_automation_built",
            source_module_id="M-050",
            severity=EventSeverity.INFO,
            payload_json={
                "learning_automation_set_id": automation_set.learning_automation_set_id,
                "learning_automation_id": record.learning_automation_id,
                "scope_type": str(payload.scope_type),
                "scope_ref": payload.scope_ref,
                "recommendation_count": len(recommendations),
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        failed_set = LearningAutomationSet(
            learning_automation_set_id=automation_set.learning_automation_set_id,
            scope_type=payload.scope_type,
            scope_ref=payload.scope_ref,
            automation_status=LearningAutomationStatus.FAILED,
        )
        session.add(failed_set)
        append_event_record(
            session,
            deal_id=payload.scope_ref if payload.scope_type == LearningAutomationScopeType.DEAL else None,
            event_code="learning_automation_failed",
            source_module_id="M-050",
            severity=EventSeverity.HIGH,
            payload_json={"learning_automation_set_id": automation_set.learning_automation_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(automation_set)
    return automation_set


def get_learning_automation_set(
    session: Session,
    learning_automation_set_id: str,
) -> tuple[LearningAutomationSet, list[tuple[LearningAutomationRecord, list[LearningRecommendationRecord]]]]:
    automation_set = _get_set(session, learning_automation_set_id)
    records = _get_records(session, learning_automation_set_id)
    return automation_set, [(record, _get_recommendations(session, record.learning_automation_id)) for record in records]


def list_learning_automation_sets(
    session: Session,
    *,
    scope_type: LearningAutomationScopeType | None = None,
    scope_ref: str | None = None,
) -> list[tuple[LearningAutomationSet, list[tuple[LearningAutomationRecord, list[LearningRecommendationRecord]]]]]:
    query = select(LearningAutomationSet).order_by(LearningAutomationSet.created_at.desc())
    if scope_type:
        query = query.where(LearningAutomationSet.scope_type == scope_type)
    if scope_ref:
        query = query.where(LearningAutomationSet.scope_ref == scope_ref)
    sets = list(session.scalars(query))
    return [get_learning_automation_set(session, item.learning_automation_set_id) for item in sets]


def get_learning_automation_record(
    session: Session,
    learning_automation_id: str,
) -> tuple[LearningAutomationRecord, list[LearningRecommendationRecord]]:
    record = _get_record(session, learning_automation_id)
    return record, _get_recommendations(session, learning_automation_id)
