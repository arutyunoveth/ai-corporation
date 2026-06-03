from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.cost_model.models import CostModelSet
from src.modules.deal_closure.service import get_deal_closure_set
from src.modules.deal_registry.models import Deal
from src.modules.event_log.service import append_event_record
from src.modules.kpi_learning.models import KPILearningRecord, KPILearningSet, LearningNoteRecord
from src.modules.kpi_learning.schemas import BuildKPILearningRequest
from src.modules.payment_collection.models import PaymentCollectionEvent
from src.modules.quote_repository.models import QuoteRecord, QuoteSet
from src.shared.closure_package import load_closure_package
from src.shared.db.base import utcnow
from src.shared.enums import DealClosureStatus, EventSeverity, KPIStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_kpi_learning_id, next_kpi_learning_set_id, next_learning_note_id
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, kpi_learning_set_id: str) -> KPILearningSet:
    record = session.scalar(select(KPILearningSet).where(KPILearningSet.kpi_learning_set_id == kpi_learning_set_id))
    if not record:
        raise NotFoundError(f"KPI learning set '{kpi_learning_set_id}' was not found")
    return record


def _get_record(session: Session, kpi_learning_id: str) -> KPILearningRecord:
    record = session.scalar(select(KPILearningRecord).where(KPILearningRecord.kpi_learning_id == kpi_learning_id))
    if not record:
        raise NotFoundError(f"KPI learning record '{kpi_learning_id}' was not found")
    return record


def _get_records(session: Session, kpi_learning_set_id: str) -> list[KPILearningRecord]:
    return list(
        session.scalars(
            select(KPILearningRecord)
            .where(KPILearningRecord.kpi_learning_set_id == kpi_learning_set_id)
            .order_by(KPILearningRecord.created_at.asc(), KPILearningRecord.id.asc())
        )
    )


def _get_notes(session: Session, kpi_learning_id: str) -> list[LearningNoteRecord]:
    return list(
        session.scalars(
            select(LearningNoteRecord)
            .where(LearningNoteRecord.kpi_learning_id == kpi_learning_id)
            .order_by(LearningNoteRecord.created_at.asc(), LearningNoteRecord.id.asc())
        )
    )


def build_kpi_learning(session: Session, payload: BuildKPILearningRequest) -> KPILearningSet:
    closure_set, closure_records, _snapshots = get_deal_closure_set(session, payload.deal_closure_set_id)
    require_same_reference(payload.deal_id, closure_set.deal_id, "deal_id")
    if str(closure_set.closure_status) != str(DealClosureStatus.CLOSED):
        raise ValidationError("KPI learning requires a CLOSED deal closure set")
    if not closure_records:
        raise ValidationError("KPI learning requires a closed deal closure record")

    closure_record = closure_records[-1]
    package = load_closure_package(
        session,
        deal_id=payload.deal_id,
        outcome_intake_set_id=closure_set.outcome_intake_set_id,
        execution_command_set_id=closure_set.execution_command_set_id,
    )
    deal = session.scalar(select(Deal).where(Deal.deal_id == payload.deal_id))
    if not deal:
        raise NotFoundError(f"Deal '{payload.deal_id}' was not found")

    cycle_time_days = (closure_record.closed_at - deal.created_at).total_seconds() / 86400
    supplier_count = int(
        session.scalar(
            select(func.count(func.distinct(QuoteRecord.supplier_id)))
            .join(QuoteSet, QuoteSet.quote_set_id == QuoteRecord.quote_set_id)
            .where(QuoteSet.deal_id == payload.deal_id)
        )
        or 0
    )
    margin_estimate = None
    if package.latest_cost_model_record and package.latest_payment_collection_record:
        margin_estimate = float(package.latest_payment_collection_record.expected_amount) - float(
            package.latest_cost_model_record.total_cost
        )
    elif package.latest_cost_model_record:
        margin_estimate = 0.0 - float(package.latest_cost_model_record.total_cost)

    payment_collection_days = None
    if package.latest_payment_collection_set:
        latest_collection_event = session.scalar(
            select(PaymentCollectionEvent)
            .where(
                PaymentCollectionEvent.payment_collection_id
                == package.latest_payment_collection_record.payment_collection_id
            )
            .order_by(PaymentCollectionEvent.event_timestamp.desc(), PaymentCollectionEvent.id.desc())
            .limit(1)
        )
        if latest_collection_event:
            payment_collection_days = (
                latest_collection_event.event_timestamp - package.latest_payment_collection_set.created_at
            ).total_seconds() / 86400

    kpi_set = KPILearningSet(
        kpi_learning_set_id=next_kpi_learning_set_id(session, KPILearningSet.kpi_learning_set_id),
        deal_id=payload.deal_id,
        deal_closure_set_id=closure_set.deal_closure_set_id,
        kpi_status=KPIStatus.BUILT,
    )
    session.add(kpi_set)
    session.flush()
    try:
        record = KPILearningRecord(
            kpi_learning_id=next_kpi_learning_id(session, KPILearningRecord.kpi_learning_id),
            kpi_learning_set_id=kpi_set.kpi_learning_set_id,
            cycle_time_days=cycle_time_days,
            margin_estimate=margin_estimate,
            supplier_count=supplier_count,
            incident_count=package.incident_count,
            payment_collection_days=payment_collection_days,
        )
        session.add(record)
        session.flush()
        for note in payload.learning_notes:
            note_record = LearningNoteRecord(
                learning_note_id=next_learning_note_id(session, LearningNoteRecord.learning_note_id),
                kpi_learning_id=record.kpi_learning_id,
                note_type=note.note_type,
                note_text=require_non_empty(note.note_text, "note_text"),
            )
            session.add(note_record)
            session.flush()
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="learning_note_recorded",
                source_module_id="M-047",
                severity=EventSeverity.INFO,
                payload_json={
                    "kpi_learning_set_id": kpi_set.kpi_learning_set_id,
                    "kpi_learning_id": record.kpi_learning_id,
                    "learning_note_id": note_record.learning_note_id,
                    "note_type": str(note.note_type),
                },
            )
        kpi_set.updated_at = utcnow()
        session.add(kpi_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="kpi_learning_built",
            source_module_id="M-047",
            severity=EventSeverity.INFO,
            payload_json={
                "kpi_learning_set_id": kpi_set.kpi_learning_set_id,
                "kpi_learning_id": record.kpi_learning_id,
                "supplier_count": supplier_count,
                "incident_count": package.incident_count,
                "cost_model_set_id": package.latest_cost_model_set.cost_model_set_id
                if package.latest_cost_model_set
                else None,
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        failed_set = session.scalar(
            select(KPILearningSet).where(KPILearningSet.kpi_learning_set_id == kpi_set.kpi_learning_set_id)
        )
        if not failed_set:
            failed_set = KPILearningSet(
                kpi_learning_set_id=kpi_set.kpi_learning_set_id,
                deal_id=payload.deal_id,
                deal_closure_set_id=closure_set.deal_closure_set_id,
                kpi_status=KPIStatus.FAILED,
            )
        else:
            failed_set.kpi_status = KPIStatus.FAILED
            failed_set.updated_at = utcnow()
        session.add(failed_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="kpi_learning_failed",
            source_module_id="M-047",
            severity=EventSeverity.HIGH,
            payload_json={"kpi_learning_set_id": kpi_set.kpi_learning_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(kpi_set)
    return kpi_set


def get_kpi_learning_set(
    session: Session,
    kpi_learning_set_id: str,
) -> tuple[KPILearningSet, list[tuple[KPILearningRecord, list[LearningNoteRecord]]]]:
    kpi_set = _get_set(session, kpi_learning_set_id)
    records = _get_records(session, kpi_learning_set_id)
    return kpi_set, [(record, _get_notes(session, record.kpi_learning_id)) for record in records]


def list_kpi_learning_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[KPILearningSet, list[tuple[KPILearningRecord, list[LearningNoteRecord]]]]]:
    query = select(KPILearningSet).order_by(KPILearningSet.created_at.desc())
    if deal_id:
        query = query.where(KPILearningSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_kpi_learning_set(session, item.kpi_learning_set_id) for item in sets]


def get_kpi_learning_record(
    session: Session,
    kpi_learning_id: str,
) -> tuple[KPILearningRecord, list[LearningNoteRecord]]:
    record = _get_record(session, kpi_learning_id)
    return record, _get_notes(session, kpi_learning_id)
