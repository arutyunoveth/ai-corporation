from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.customer_registry.models import CustomerProfile
from src.modules.deal_registry.service import get_deal
from src.modules.event_log.service import append_event_record
from src.modules.intake_priority.models import IntakePriorityFactor, IntakePriorityRecord, IntakePrioritySet
from src.modules.tender_normalization.models import TenderNormalizationLink, TenderNormalizationRecord, TenderNormalizationSet
from src.modules.tender_screening.models import TenderScreeningRecord
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, PrioritizationStatus, ScreeningResultStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_intake_priority_id, next_intake_priority_set_id


def _latest_normalization_for_deal(
    session: Session,
    deal_id: str,
) -> tuple[TenderNormalizationSet | None, TenderNormalizationRecord | None, TenderNormalizationLink | None]:
    link = session.scalar(
        select(TenderNormalizationLink)
        .where(TenderNormalizationLink.deal_id == deal_id)
        .order_by(TenderNormalizationLink.created_at.desc(), TenderNormalizationLink.id.desc())
        .limit(1)
    )
    if not link:
        return None, None, None
    record = session.scalar(
        select(TenderNormalizationRecord)
        .where(TenderNormalizationRecord.tender_normalization_id == link.tender_normalization_id)
        .limit(1)
    )
    if not record:
        return None, None, link
    normalization_set = session.scalar(
        select(TenderNormalizationSet)
        .where(TenderNormalizationSet.tender_normalization_set_id == record.tender_normalization_set_id)
        .limit(1)
    )
    return normalization_set, record, link


def _latest_screening_for_deal(session: Session, deal_id: str) -> TenderScreeningRecord | None:
    return session.scalar(
        select(TenderScreeningRecord)
        .where(TenderScreeningRecord.deal_id == deal_id)
        .order_by(TenderScreeningRecord.created_at.desc(), TenderScreeningRecord.id.desc())
        .limit(1)
    )


def _get_set(session: Session, intake_priority_set_id: str) -> IntakePrioritySet:
    record = session.scalar(
        select(IntakePrioritySet).where(IntakePrioritySet.intake_priority_set_id == intake_priority_set_id)
    )
    if not record:
        raise NotFoundError(f"Intake priority set '{intake_priority_set_id}' was not found")
    return record


def _get_record(session: Session, intake_priority_id: str) -> IntakePriorityRecord:
    record = session.scalar(
        select(IntakePriorityRecord).where(IntakePriorityRecord.intake_priority_id == intake_priority_id)
    )
    if not record:
        raise NotFoundError(f"Intake priority record '{intake_priority_id}' was not found")
    return record


def _get_records(session: Session, intake_priority_set_id: str) -> list[IntakePriorityRecord]:
    return list(
        session.scalars(
            select(IntakePriorityRecord)
            .where(IntakePriorityRecord.intake_priority_set_id == intake_priority_set_id)
            .order_by(IntakePriorityRecord.created_at.asc(), IntakePriorityRecord.id.asc())
        )
    )


def _get_factors(session: Session, intake_priority_id: str) -> list[IntakePriorityFactor]:
    return list(
        session.scalars(
            select(IntakePriorityFactor)
            .where(IntakePriorityFactor.intake_priority_id == intake_priority_id)
            .order_by(IntakePriorityFactor.created_at.asc(), IntakePriorityFactor.id.asc())
        )
    )


def build_intake_priority(session: Session, deal_id: str) -> IntakePrioritySet:
    deal = get_deal(session, deal_id)
    priority_set = IntakePrioritySet(
        intake_priority_set_id=next_intake_priority_set_id(session, IntakePrioritySet.intake_priority_set_id),
        deal_id=deal.deal_id,
        prioritization_status=PrioritizationStatus.BUILT,
    )
    session.add(priority_set)
    session.flush()
    try:
        normalization_set, normalization_record, normalization_link = _latest_normalization_for_deal(session, deal.deal_id)
        if not normalization_record:
            raise ValidationError("Intake priority requires canonical tender normalization context")
        screening = _latest_screening_for_deal(session, deal.deal_id)
        customer = (
            session.scalar(select(CustomerProfile).where(CustomerProfile.customer_id == normalization_link.customer_id))
            if normalization_link and normalization_link.customer_id
            else None
        )

        completeness_factor = 1.0 if normalization_record.normalized_procurement_number and normalization_record.normalized_customer_name and normalization_record.normalized_title else 0.45
        deadline_factor = 0.8 if normalization_record.normalized_deadline_at else 0.5
        screening_factor = 0.5
        if screening:
            if screening.result_status == ScreeningResultStatus.PASS:
                screening_factor = 0.95
            elif screening.result_status == ScreeningResultStatus.NEEDS_REVIEW:
                screening_factor = 0.6
            else:
                screening_factor = 0.1
        customer_factor = 0.75 if customer and customer.customer_status == "ACTIVE" else 0.55
        strategic_factor = 0.8 if deal.domain_type == "ELECTRICAL_EQUIPMENT" else 0.5
        score = round(
            (completeness_factor * 0.25 + deadline_factor * 0.15 + screening_factor * 0.25 + customer_factor * 0.15 + strategic_factor * 0.2)
            * 100,
            2,
        )
        recommended_queue_position = 1 if score >= 80 else 2 if score >= 60 else 3
        summary_text = (
            f"Canonical intake priority for deal {deal.deal_id}: score={score}, "
            f"queue_position=P{recommended_queue_position}, "
            f"normalized_title='{normalization_record.normalized_title}'."
        )
        record = IntakePriorityRecord(
            intake_priority_id=next_intake_priority_id(session, IntakePriorityRecord.intake_priority_id),
            intake_priority_set_id=priority_set.intake_priority_set_id,
            priority_score=score,
            summary_text=summary_text,
            recommended_queue_position=recommended_queue_position,
        )
        session.add(record)
        session.flush()

        factors = [
            ("COMPLETENESS", completeness_factor, "Normalized procurement number, customer, and title presence."),
            ("DEADLINE_SIGNAL", deadline_factor, "Availability of normalized deadline context."),
            ("SCREENING_SIGNAL", screening_factor, "Latest available screening result, if present."),
            ("CUSTOMER_SIGNAL", customer_factor, "Customer registry confidence and activity state."),
            ("STRATEGIC_SIGNAL", strategic_factor, "Domain fit and strategic relevance heuristic."),
        ]
        for factor_code, factor_value, rationale in factors:
            session.add(
                IntakePriorityFactor(
                    intake_priority_id=record.intake_priority_id,
                    factor_code=factor_code,
                    factor_value=factor_value,
                    rationale=rationale,
                )
            )

        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="intake_priority_built",
            source_module_id="M-010",
            severity=EventSeverity.INFO,
            payload_json={
                "intake_priority_set_id": priority_set.intake_priority_set_id,
                "intake_priority_id": record.intake_priority_id,
                "tender_normalization_set_id": normalization_set.tender_normalization_set_id if normalization_set else None,
                "priority_score": score,
            },
        )
        session.commit()
        session.refresh(priority_set)
        return priority_set
    except Exception as exc:
        priority_set.prioritization_status = PrioritizationStatus.FAILED
        priority_set.updated_at = utcnow()
        append_event_record(
            session,
            deal_id=deal.deal_id,
            event_code="intake_priority_failed",
            source_module_id="M-010",
            severity=EventSeverity.HIGH,
            payload_json={"intake_priority_set_id": priority_set.intake_priority_set_id, "error": str(exc)},
        )
        session.commit()
        raise


def get_intake_priority_set(
    session: Session,
    intake_priority_set_id: str,
) -> tuple[IntakePrioritySet, list[tuple[IntakePriorityRecord, list[IntakePriorityFactor]]]]:
    priority_set = _get_set(session, intake_priority_set_id)
    records = [(record, _get_factors(session, record.intake_priority_id)) for record in _get_records(session, intake_priority_set_id)]
    return priority_set, records


def get_intake_priority_record(
    session: Session,
    intake_priority_id: str,
) -> tuple[IntakePriorityRecord, list[IntakePriorityFactor]]:
    record = _get_record(session, intake_priority_id)
    return record, _get_factors(session, intake_priority_id)


def list_intake_priority_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[IntakePrioritySet, list[tuple[IntakePriorityRecord, list[IntakePriorityFactor]]]]]:
    query = select(IntakePrioritySet).order_by(IntakePrioritySet.created_at.desc(), IntakePrioritySet.id.desc())
    if deal_id:
        query = query.where(IntakePrioritySet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_intake_priority_set(session, item.intake_priority_set_id) for item in sets]
