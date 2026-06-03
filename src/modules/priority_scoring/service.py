from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.priority_scoring.models import PriorityScoreRecord
from src.modules.priority_scoring.schemas import RunPriorityScoringRequest
from src.modules.tender_screening.service import get_screening
from src.shared.analysis_package import load_intake_package
from src.shared.enums import EventSeverity, PriorityBucket, ScreeningResultStatus
from src.shared.ids import next_priority_score_id
from src.shared.validation import require_same_reference


def _compute_priority(package, screening) -> tuple[float, PriorityBucket, dict, str]:
    if screening.result_status == ScreeningResultStatus.FAIL:
        return 0.0, PriorityBucket.REJECT, {"screening_gate": 0.0}, "Rejected at screening stage."

    urgency_score = 0.9 if package.document_set.item_count >= 2 else 0.55
    value_score = 0.8 if package.deal.domain_type == "ELECTRICAL_EQUIPMENT" else 0.4
    data_quality_score = 0.9 if package.deal.procurement_number else 0.45
    screening_score = float(screening.screening_score)
    source_score = 0.85 if str(package.intake.source_type) in {"PORTAL", "MANUAL"} else 0.65

    score = round(
        (urgency_score * 0.25 + value_score * 0.2 + data_quality_score * 0.2 + screening_score * 0.25 + source_score * 0.1)
        * 100,
        2,
    )
    factor_breakdown = {
        "urgency_score": urgency_score,
        "value_score": value_score,
        "data_quality_score": data_quality_score,
        "screening_score": screening_score,
        "source_score": source_score,
    }
    if screening.result_status == ScreeningResultStatus.NEEDS_REVIEW:
        bucket = PriorityBucket.LOW if score < 75 else PriorityBucket.MEDIUM
        rationale = "Candidate is potentially relevant but still requires manual clarification before deep work."
        return score, bucket, factor_breakdown, rationale

    if score >= 75:
        bucket = PriorityBucket.HIGH
    elif score >= 50:
        bucket = PriorityBucket.MEDIUM
    else:
        bucket = PriorityBucket.LOW
    rationale = "Priority is derived from screening quality, document readiness, source quality, and deal metadata completeness."
    return score, bucket, factor_breakdown, rationale


def run_priority_scoring(session: Session, payload: RunPriorityScoringRequest) -> PriorityScoreRecord:
    package = load_intake_package(
        session,
        deal_id=payload.deal_id,
        intake_id=payload.intake_id,
        document_set_id=payload.document_set_id,
        tender_summary_id=payload.tender_summary_id,
    )
    screening = get_screening(session, payload.screening_id)
    require_same_reference(package.deal.deal_id, screening.deal_id, "deal_id")
    require_same_reference(package.intake.intake_id, screening.intake_id, "intake_id")
    append_event_record(
        session,
        deal_id=package.deal.deal_id,
        event_code="priority_scoring_started",
        source_module_id="M-010",
        severity=EventSeverity.INFO,
        payload_json={"screening_id": screening.screening_id},
    )
    try:
        priority_score, priority_bucket, factor_breakdown, rationale_text = _compute_priority(package, screening)
        record = PriorityScoreRecord(
            priority_score_id=next_priority_score_id(session, PriorityScoreRecord.priority_score_id),
            deal_id=package.deal.deal_id,
            intake_id=package.intake.intake_id,
            document_set_id=package.document_set.document_set_id,
            tender_summary_id=package.tender_summary.tender_summary_id,
            screening_id=screening.screening_id,
            priority_score=priority_score,
            priority_bucket=priority_bucket,
            rationale_text=rationale_text,
            factor_breakdown_json=factor_breakdown,
        )
        session.add(record)
        session.flush()
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="priority_scoring_completed",
            source_module_id="M-010",
            severity=EventSeverity.INFO,
            payload_json={
                "priority_score_id": record.priority_score_id,
                "priority_bucket": str(priority_bucket),
                "priority_score": priority_score,
            },
        )
        session.commit()
        session.refresh(record)
        return record
    except Exception as exc:
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="priority_scoring_failed",
            source_module_id="M-010",
            severity=EventSeverity.HIGH,
            payload_json={"screening_id": screening.screening_id, "error": str(exc)},
        )
        session.commit()
        raise


def get_priority_score(session: Session, priority_score_id: str) -> PriorityScoreRecord:
    from src.shared.errors import NotFoundError

    record = session.scalar(
        select(PriorityScoreRecord).where(PriorityScoreRecord.priority_score_id == priority_score_id)
    )
    if not record:
        raise NotFoundError(f"Priority score '{priority_score_id}' was not found")
    return record


def list_priority_scores(session: Session, *, deal_id: str | None = None) -> list[PriorityScoreRecord]:
    query = select(PriorityScoreRecord).order_by(PriorityScoreRecord.created_at.desc())
    if deal_id:
        query = query.where(PriorityScoreRecord.deal_id == deal_id)
    return list(session.scalars(query))

