from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.tender_screening.models import TenderScreeningRecord
from src.modules.tender_screening.schemas import RunScreeningRequest
from src.shared.analysis_package import load_intake_package
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, ScreeningResultStatus
from src.shared.ids import next_screening_id


def _compute_screening(package) -> tuple[ScreeningResultStatus, float, dict, list[str], str, str | None]:
    domain_fit_score = 1.0 if package.deal.domain_type == "ELECTRICAL_EQUIPMENT" else 0.1
    document_presence_score = 1.0 if package.document_set.item_count > 0 else 0.0
    procurement_score = 1.0 if package.deal.procurement_number else 0.4
    summary_score = 1.0 if package.tender_summary.structured_summary_json.get("high_level_scope") else 0.5
    source_score = {
        "PORTAL": 1.0,
        "MANUAL": 0.9,
        "EMAIL": 0.8,
        "API": 0.75,
        "OTHER": 0.5,
    }.get(str(package.intake.source_type), 0.5)
    factor_breakdown = {
        "domain_fit_score": domain_fit_score,
        "document_presence_score": document_presence_score,
        "procurement_score": procurement_score,
        "summary_score": summary_score,
        "source_score": source_score,
    }
    screening_score = round(
        (
            domain_fit_score * 0.35
            + document_presence_score * 0.2
            + procurement_score * 0.2
            + summary_score * 0.15
            + source_score * 0.1
        ),
        4,
    )
    reason_codes: list[str] = []

    if package.deal.domain_type != "ELECTRICAL_EQUIPMENT":
        reason_codes.append("NON_TARGET_DOMAIN")
        return (
            ScreeningResultStatus.FAIL,
            screening_score,
            factor_breakdown,
            reason_codes,
            "Deal is outside the current MVP electrical equipment supply perimeter.",
            "REJECTED_EARLY",
        )

    if not package.deal.procurement_number:
        reason_codes.append("MISSING_PROCUREMENT_NUMBER")
    if package.document_set.item_count < 2:
        reason_codes.append("LIMITED_DOCUMENT_SET")
    if package.intake.source_type == "OTHER":
        reason_codes.append("LOW_SOURCE_RELIABILITY")

    if "MISSING_PROCUREMENT_NUMBER" in reason_codes or "LIMITED_DOCUMENT_SET" in reason_codes:
        return (
            ScreeningResultStatus.NEEDS_REVIEW,
            screening_score,
            factor_breakdown,
            reason_codes,
            "Deal has potential, but the intake package is incomplete for confident auto-qualification.",
            None,
        )

    return (
        ScreeningResultStatus.PASS,
        screening_score,
        factor_breakdown,
        reason_codes,
        "Deal fits the current MVP perimeter and has a minimally sufficient intake package.",
        "CANDIDATE",
    )


def run_screening(session: Session, payload: RunScreeningRequest) -> TenderScreeningRecord:
    package = load_intake_package(
        session,
        deal_id=payload.deal_id,
        intake_id=payload.intake_id,
        document_set_id=payload.document_set_id,
        tender_summary_id=payload.tender_summary_id,
    )
    append_event_record(
        session,
        deal_id=package.deal.deal_id,
        event_code="tender_screening_started",
        source_module_id="M-009",
        severity=EventSeverity.INFO,
        payload_json={
            "intake_id": package.intake.intake_id,
            "document_set_id": package.document_set.document_set_id,
            "tender_summary_id": package.tender_summary.tender_summary_id,
        },
    )
    try:
        result_status, screening_score, factor_breakdown, reason_codes, rationale_text, recommended_next_status = _compute_screening(
            package
        )
        screening = TenderScreeningRecord(
            screening_id=next_screening_id(session, TenderScreeningRecord.screening_id),
            deal_id=package.deal.deal_id,
            intake_id=package.intake.intake_id,
            document_set_id=package.document_set.document_set_id,
            tender_summary_id=package.tender_summary.tender_summary_id,
            result_status=result_status,
            screening_score=screening_score,
            rationale_text=rationale_text,
            factor_breakdown_json=factor_breakdown,
            reason_codes_json=reason_codes,
            recommended_next_status=recommended_next_status,
        )
        session.add(screening)
        session.flush()
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="tender_screening_completed",
            source_module_id="M-009",
            severity=EventSeverity.INFO,
            payload_json={
                "screening_id": screening.screening_id,
                "result_status": str(result_status),
                "recommended_next_status": recommended_next_status,
            },
        )
        session.commit()
        session.refresh(screening)
        return screening
    except Exception as exc:
        append_event_record(
            session,
            deal_id=package.deal.deal_id,
            event_code="tender_screening_failed",
            source_module_id="M-009",
            severity=EventSeverity.HIGH,
            payload_json={"error": str(exc)},
        )
        session.commit()
        raise


def get_screening(session: Session, screening_id: str) -> TenderScreeningRecord:
    from src.shared.errors import NotFoundError

    screening = session.scalar(select(TenderScreeningRecord).where(TenderScreeningRecord.screening_id == screening_id))
    if not screening:
        raise NotFoundError(f"Screening '{screening_id}' was not found")
    return screening


def list_screenings(session: Session, *, deal_id: str | None = None) -> list[TenderScreeningRecord]:
    query = select(TenderScreeningRecord).order_by(TenderScreeningRecord.created_at.desc())
    if deal_id:
        query = query.where(TenderScreeningRecord.deal_id == deal_id)
    return list(session.scalars(query))

