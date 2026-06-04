from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.postmortems.models import PostmortemFinding, PostmortemRecord, PostmortemSet
from src.modules.supplier_ratings.models import (
    SupplierRatingFactor,
    SupplierRatingUpdateRecord,
    SupplierRatingUpdateSet,
)
from src.modules.supplier_ratings.schemas import BuildSupplierRatingUpdateRequest
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, RiskSeverity, SupplierRatingBand, SupplierRatingStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.final_recovery_package import load_final_recovery_context
from src.shared.ids import next_supplier_rating_update_id, next_supplier_rating_update_set_id


def _get_set(session: Session, supplier_rating_update_set_id: str) -> SupplierRatingUpdateSet:
    record = session.scalar(
        select(SupplierRatingUpdateSet).where(
            SupplierRatingUpdateSet.supplier_rating_update_set_id == supplier_rating_update_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Supplier rating update set '{supplier_rating_update_set_id}' was not found")
    return record


def _get_record(session: Session, supplier_rating_update_id: str) -> SupplierRatingUpdateRecord:
    record = session.scalar(
        select(SupplierRatingUpdateRecord).where(
            SupplierRatingUpdateRecord.supplier_rating_update_id == supplier_rating_update_id
        )
    )
    if not record:
        raise NotFoundError(f"Supplier rating update record '{supplier_rating_update_id}' was not found")
    return record


def _get_records(session: Session, supplier_rating_update_set_id: str) -> list[SupplierRatingUpdateRecord]:
    return list(
        session.scalars(
            select(SupplierRatingUpdateRecord)
            .where(SupplierRatingUpdateRecord.supplier_rating_update_set_id == supplier_rating_update_set_id)
            .order_by(SupplierRatingUpdateRecord.created_at.asc(), SupplierRatingUpdateRecord.id.asc())
        )
    )


def _get_factors(session: Session, supplier_rating_update_id: str) -> list[SupplierRatingFactor]:
    return list(
        session.scalars(
            select(SupplierRatingFactor)
            .where(SupplierRatingFactor.supplier_rating_update_id == supplier_rating_update_id)
            .order_by(SupplierRatingFactor.created_at.asc(), SupplierRatingFactor.id.asc())
        )
    )


def build_supplier_rating_update(session: Session, payload: BuildSupplierRatingUpdateRequest) -> SupplierRatingUpdateSet:
    context = load_final_recovery_context(session, payload.deal_id)
    if not context.supplier_contract_set or not context.supplier_contract_record:
        raise ValidationError("Supplier rating update requires canonical supplier contract context")
    postmortem_set = session.scalar(
        select(PostmortemSet).where(PostmortemSet.deal_id == payload.deal_id).order_by(PostmortemSet.created_at.desc(), PostmortemSet.id.desc())
    )
    if not postmortem_set:
        raise ValidationError("Supplier rating update requires canonical postmortem context")
    postmortem_record = session.scalar(
        select(PostmortemRecord)
        .where(PostmortemRecord.postmortem_set_id == postmortem_set.postmortem_set_id)
        .order_by(PostmortemRecord.created_at.desc(), PostmortemRecord.id.desc())
    )
    if not postmortem_record:
        raise ValidationError("Supplier rating update requires postmortem record")
    findings = list(
        session.scalars(
            select(PostmortemFinding)
            .where(PostmortemFinding.postmortem_id == postmortem_record.postmortem_id)
            .order_by(PostmortemFinding.created_at.asc(), PostmortemFinding.id.asc())
        )
    )
    score = 80.0
    factors: list[tuple[str, float, str]] = [
        ("CONTRACT_READINESS", 30.0, "Supplier reached signed contractual execution state."),
        ("DELIVERY_SIGNAL", 30.0, "Execution branch reached delivery and acceptance checkpoints."),
        ("POSTMORTEM_SIGNAL", 20.0, "Postmortem was captured and can feed supplier memory."),
    ]
    if context.claim_trigger_set and str(context.claim_trigger_set.trigger_status) == "TRIGGERED":
        score -= 25.0
        factors.append(("CLAIM_DEDUCTION", -25.0, "Claim trigger reduced the supplier trust score."))
    if any(item.severity in {RiskSeverity.HIGH, RiskSeverity.CRITICAL} for item in findings):
        score -= 20.0
        factors.append(("HIGH_RISK_FINDING", -20.0, "High-severity postmortem finding reduced supplier score."))
    if context.incident_register_set:
        score -= 5.0
        factors.append(("INCIDENT_HISTORY", -5.0, "Incident register history reduced supplier score slightly."))
    score = max(0.0, min(100.0, score))
    if score >= 85:
        band = SupplierRatingBand.PREFERRED
        status = SupplierRatingStatus.UPDATED
    elif score >= 70:
        band = SupplierRatingBand.APPROVED
        status = SupplierRatingStatus.UPDATED
    elif score >= 50:
        band = SupplierRatingBand.WATCHLIST
        status = SupplierRatingStatus.NEEDS_REVIEW
    else:
        band = SupplierRatingBand.BLOCKED
        status = SupplierRatingStatus.NEEDS_REVIEW

    rating_set = SupplierRatingUpdateSet(
        supplier_rating_update_set_id=next_supplier_rating_update_set_id(
            session, SupplierRatingUpdateSet.supplier_rating_update_set_id
        ),
        deal_id=payload.deal_id,
        supplier_id=context.supplier_contract_set.supplier_id,
        supplier_contract_set_id=context.supplier_contract_set.supplier_contract_set_id,
        postmortem_set_id=postmortem_set.postmortem_set_id,
        rating_status=status,
    )
    session.add(rating_set)
    session.flush()
    try:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_rating_set_created",
            source_module_id="M-047",
            severity=EventSeverity.INFO,
            payload_json={"supplier_rating_update_set_id": rating_set.supplier_rating_update_set_id},
        )
        record = SupplierRatingUpdateRecord(
            supplier_rating_update_id=next_supplier_rating_update_id(
                session, SupplierRatingUpdateRecord.supplier_rating_update_id
            ),
            supplier_rating_update_set_id=rating_set.supplier_rating_update_set_id,
            prior_rating_value=None,
            updated_rating_value=score,
            rating_band=band,
            rationale_text=postmortem_record.recommendation_summary,
        )
        session.add(record)
        session.flush()
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_rating_record_created",
            source_module_id="M-047",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_rating_update_set_id": rating_set.supplier_rating_update_set_id,
                "supplier_rating_update_id": record.supplier_rating_update_id,
                "supplier_id": rating_set.supplier_id,
            },
        )
        for factor_code, factor_score, summary in factors:
            session.add(
                SupplierRatingFactor(
                    supplier_rating_update_id=record.supplier_rating_update_id,
                    factor_code=factor_code,
                    factor_score=factor_score,
                    summary=summary,
                )
            )
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_rating_status_changed",
            source_module_id="M-047",
            severity=EventSeverity.INFO,
            payload_json={
                "supplier_rating_update_set_id": rating_set.supplier_rating_update_set_id,
                "rating_status": str(rating_set.rating_status),
                "rating_band": str(band),
            },
        )
        if status == SupplierRatingStatus.NEEDS_REVIEW:
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="supplier_rating_exception_detected",
                source_module_id="M-047",
                severity=EventSeverity.WARNING,
                payload_json={"supplier_rating_update_set_id": rating_set.supplier_rating_update_set_id},
            )
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_rating_handoff_created",
            source_module_id="M-047",
            severity=EventSeverity.INFO,
            payload_json={"supplier_rating_update_set_id": rating_set.supplier_rating_update_set_id, "downstream_module_id": "M-048"},
        )
        rating_set.updated_at = utcnow()
        session.add(rating_set)
        session.commit()
    except Exception as exc:
        session.rollback()
        failed = session.scalar(
            select(SupplierRatingUpdateSet).where(
                SupplierRatingUpdateSet.supplier_rating_update_set_id == rating_set.supplier_rating_update_set_id
            )
        )
        if failed:
            failed.rating_status = SupplierRatingStatus.FAILED
            failed.updated_at = utcnow()
            session.add(failed)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="supplier_rating_failed",
            source_module_id="M-047",
            severity=EventSeverity.HIGH,
            payload_json={"supplier_rating_update_set_id": rating_set.supplier_rating_update_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(rating_set)
    return rating_set


def get_supplier_rating_update_set(
    session: Session,
    supplier_rating_update_set_id: str,
) -> tuple[SupplierRatingUpdateSet, list[tuple[SupplierRatingUpdateRecord, list[SupplierRatingFactor]]]]:
    rating_set = _get_set(session, supplier_rating_update_set_id)
    records = _get_records(session, supplier_rating_update_set_id)
    return rating_set, [(record, _get_factors(session, record.supplier_rating_update_id)) for record in records]


def list_supplier_rating_update_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[SupplierRatingUpdateSet, list[tuple[SupplierRatingUpdateRecord, list[SupplierRatingFactor]]]]]:
    query = select(SupplierRatingUpdateSet).order_by(
        SupplierRatingUpdateSet.created_at.desc(), SupplierRatingUpdateSet.id.desc()
    )
    if deal_id:
        query = query.where(SupplierRatingUpdateSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_supplier_rating_update_set(session, item.supplier_rating_update_set_id) for item in sets]


def get_supplier_rating_update_record(
    session: Session,
    supplier_rating_update_id: str,
) -> tuple[SupplierRatingUpdateRecord, list[SupplierRatingFactor]]:
    record = _get_record(session, supplier_rating_update_id)
    return record, _get_factors(session, supplier_rating_update_id)
