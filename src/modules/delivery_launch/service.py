from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.delivery_launch.models import DeliveryLaunchFlag, DeliveryLaunchRecord, DeliveryLaunchSet
from src.modules.delivery_launch.schemas import BuildDeliveryLaunchRequest, LaunchDeliveryRequest
from src.modules.event_log.service import append_event_record
from src.modules.submission_receipts.models import SubmissionReceiptSet
from src.shared.db.base import utcnow
from src.shared.enums import DeliveryLaunchStatus, EventSeverity, LaunchRecommendation, OutcomeCode, RiskSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.execution_package import load_execution_package
from src.shared.ids import next_delivery_launch_id, next_delivery_launch_set_id
from src.shared.validation import require_non_empty, require_same_reference


def _get_set(session: Session, delivery_launch_set_id: str) -> DeliveryLaunchSet:
    record = session.scalar(select(DeliveryLaunchSet).where(DeliveryLaunchSet.delivery_launch_set_id == delivery_launch_set_id))
    if not record:
        raise NotFoundError(f"Delivery launch set '{delivery_launch_set_id}' was not found")
    return record


def _get_record(session: Session, delivery_launch_id: str) -> DeliveryLaunchRecord:
    record = session.scalar(select(DeliveryLaunchRecord).where(DeliveryLaunchRecord.delivery_launch_id == delivery_launch_id))
    if not record:
        raise NotFoundError(f"Delivery launch record '{delivery_launch_id}' was not found")
    return record


def _get_records(session: Session, delivery_launch_set_id: str) -> list[DeliveryLaunchRecord]:
    return list(
        session.scalars(
            select(DeliveryLaunchRecord)
            .where(DeliveryLaunchRecord.delivery_launch_set_id == delivery_launch_set_id)
            .order_by(DeliveryLaunchRecord.created_at.asc(), DeliveryLaunchRecord.id.asc())
        )
    )


def _get_flags(session: Session, delivery_launch_id: str) -> list[DeliveryLaunchFlag]:
    return list(
        session.scalars(
            select(DeliveryLaunchFlag)
            .where(DeliveryLaunchFlag.delivery_launch_id == delivery_launch_id)
            .order_by(DeliveryLaunchFlag.created_at.asc(), DeliveryLaunchFlag.id.asc())
        )
    )


def build_delivery_launch(session: Session, payload: BuildDeliveryLaunchRequest) -> DeliveryLaunchSet:
    package = load_execution_package(session, deal_id=payload.deal_id, outcome_intake_set_id=payload.outcome_intake_set_id)
    if str(package.outcome_record.outcome_code) != str(OutcomeCode.WON):
        raise ValidationError("Delivery launch can be opened only from an explicit WON outcome")

    launch_set = DeliveryLaunchSet(
        delivery_launch_set_id=next_delivery_launch_set_id(session, DeliveryLaunchSet.delivery_launch_set_id),
        deal_id=payload.deal_id,
        outcome_intake_set_id=package.outcome_set.outcome_intake_set_id,
        launch_status=DeliveryLaunchStatus.READY,
    )
    session.add(launch_set)
    session.flush()
    try:
        flags: list[dict] = []
        recommendation = LaunchRecommendation.READY
        if not package.quote_recommendation or not package.recommended_quote:
            recommendation = LaunchRecommendation.NEEDS_REVIEW
            flags.append(
                {
                    "flag_code": "WINNER_LINK_MISSING",
                    "severity": RiskSeverity.MEDIUM,
                    "summary": "Awarded outcome exists but there is no persisted winning supplier/quote recommendation.",
                    "source_ref": package.outcome_set.outcome_intake_set_id,
                }
            )
        if not package.latest_bid_package_set:
            recommendation = LaunchRecommendation.BLOCKED
            flags.append(
                {
                    "flag_code": "BID_PACKAGE_CONTEXT_MISSING",
                    "severity": RiskSeverity.HIGH,
                    "summary": "No persisted bid package context was found for the awarded deal.",
                    "source_ref": package.outcome_set.outcome_intake_set_id,
                }
            )
        receipt_exists = session.scalar(
            select(SubmissionReceiptSet.id)
            .where(SubmissionReceiptSet.deal_id == payload.deal_id)
            .order_by(SubmissionReceiptSet.created_at.desc())
            .limit(1)
        )
        if not receipt_exists:
            if recommendation == LaunchRecommendation.READY:
                recommendation = LaunchRecommendation.NEEDS_REVIEW
            flags.append(
                {
                    "flag_code": "SUBMISSION_RECEIPT_CONTEXT_MISSING",
                    "severity": RiskSeverity.LOW,
                    "summary": "No persisted submission receipt context was found for this awarded deal.",
                    "source_ref": package.outcome_set.outcome_intake_set_id,
                }
            )

        summary_text = (
            f"Execution launch prepared from awarded outcome {package.outcome_record.outcome_code}. "
            f"Recommendation={recommendation}. Flags={len(flags)}."
        )
        record = DeliveryLaunchRecord(
            delivery_launch_id=next_delivery_launch_id(session, DeliveryLaunchRecord.delivery_launch_id),
            delivery_launch_set_id=launch_set.delivery_launch_set_id,
            launch_recommendation=recommendation,
            summary_text=summary_text,
        )
        session.add(record)
        session.flush()
        for flag in flags:
            session.add(DeliveryLaunchFlag(delivery_launch_id=record.delivery_launch_id, **flag))
        launch_set.launch_status = (
            DeliveryLaunchStatus.READY if recommendation == LaunchRecommendation.READY else DeliveryLaunchStatus.BLOCKED
        )
        launch_set.updated_at = utcnow()
        session.add(launch_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="delivery_launch_built",
            source_module_id="M-039",
            severity=EventSeverity.INFO,
            payload_json={
                "delivery_launch_set_id": launch_set.delivery_launch_set_id,
                "delivery_launch_id": record.delivery_launch_id,
                "launch_recommendation": str(recommendation),
                "flag_count": len(flags),
            },
        )
        session.commit()
    except Exception as exc:
        launch_set.launch_status = DeliveryLaunchStatus.FAILED
        launch_set.updated_at = utcnow()
        session.add(launch_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="delivery_launch_failed",
            source_module_id="M-039",
            severity=EventSeverity.HIGH,
            payload_json={"delivery_launch_set_id": launch_set.delivery_launch_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(launch_set)
    return launch_set


def launch_delivery(session: Session, payload: LaunchDeliveryRequest) -> DeliveryLaunchSet:
    launch_set = _get_set(session, payload.delivery_launch_set_id)
    records = _get_records(session, launch_set.delivery_launch_set_id)
    if not records:
        raise ValidationError("Delivery launch set has no launch record")
    latest_record = records[-1]
    if str(launch_set.launch_status) == str(DeliveryLaunchStatus.LAUNCHED):
        raise ValidationError("Delivery launch is already marked as LAUNCHED")
    if str(latest_record.launch_recommendation) == str(LaunchRecommendation.BLOCKED):
        raise ValidationError("Blocked delivery launch cannot be started")

    launch_set.launch_status = DeliveryLaunchStatus.LAUNCHED
    launch_set.updated_at = utcnow()
    session.add(launch_set)
    append_event_record(
        session,
        deal_id=launch_set.deal_id,
        event_code="delivery_launch_started",
        source_module_id="M-039",
        severity=EventSeverity.INFO,
        payload_json={
            "delivery_launch_set_id": launch_set.delivery_launch_set_id,
            "delivery_launch_id": latest_record.delivery_launch_id,
            "launched_by_ref": require_non_empty(payload.launched_by_ref, "launched_by_ref") if payload.launched_by_ref else None,
        },
    )
    session.commit()
    session.refresh(launch_set)
    return launch_set


def get_delivery_launch_set(
    session: Session,
    delivery_launch_set_id: str,
) -> tuple[DeliveryLaunchSet, list[tuple[DeliveryLaunchRecord, list[DeliveryLaunchFlag]]]]:
    launch_set = _get_set(session, delivery_launch_set_id)
    records = _get_records(session, delivery_launch_set_id)
    return launch_set, [(record, _get_flags(session, record.delivery_launch_id)) for record in records]


def list_delivery_launch_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[DeliveryLaunchSet, list[tuple[DeliveryLaunchRecord, list[DeliveryLaunchFlag]]]]]:
    query = select(DeliveryLaunchSet).order_by(DeliveryLaunchSet.created_at.desc())
    if deal_id:
        query = query.where(DeliveryLaunchSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_delivery_launch_set(session, item.delivery_launch_set_id) for item in sets]


def get_delivery_launch_record(
    session: Session,
    delivery_launch_id: str,
) -> tuple[DeliveryLaunchRecord, list[DeliveryLaunchFlag]]:
    record = _get_record(session, delivery_launch_id)
    launch_set = _get_set(session, record.delivery_launch_set_id)
    require_same_reference(record.delivery_launch_set_id, launch_set.delivery_launch_set_id, "delivery_launch_set_id")
    return record, _get_flags(session, delivery_launch_id)
