from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.claim_triggers.models import (
    ClaimTriggerFlag,
    ClaimTriggerLink,
    ClaimTriggerRecord,
    ClaimTriggerSet,
)
from src.modules.claim_triggers.schemas import BuildClaimTriggerRequest
from src.modules.closing_docs.models import ClosingDocsSet
from src.modules.event_log.service import append_event_record
from src.modules.incident_register.models import IncidentRegisterSet
from src.modules.payment_tracking.models import PaymentTrackingRecord, PaymentTrackingSet
from src.shared.db.base import utcnow
from src.shared.enums import ClaimTriggerStatus, EventSeverity, PaymentTrackingStatus, RiskSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_claim_trigger_id, next_claim_trigger_set_id


def _get_set(session: Session, claim_trigger_set_id: str) -> ClaimTriggerSet:
    record = session.scalar(select(ClaimTriggerSet).where(ClaimTriggerSet.claim_trigger_set_id == claim_trigger_set_id))
    if not record:
        raise NotFoundError(f"Claim trigger set '{claim_trigger_set_id}' was not found")
    return record


def _get_record(session: Session, claim_trigger_id: str) -> ClaimTriggerRecord:
    record = session.scalar(select(ClaimTriggerRecord).where(ClaimTriggerRecord.claim_trigger_id == claim_trigger_id))
    if not record:
        raise NotFoundError(f"Claim trigger record '{claim_trigger_id}' was not found")
    return record


def _get_records(session: Session, claim_trigger_set_id: str) -> list[ClaimTriggerRecord]:
    return list(
        session.scalars(
            select(ClaimTriggerRecord)
            .where(ClaimTriggerRecord.claim_trigger_set_id == claim_trigger_set_id)
            .order_by(ClaimTriggerRecord.created_at.asc(), ClaimTriggerRecord.id.asc())
        )
    )


def _get_flags(session: Session, claim_trigger_id: str) -> list[ClaimTriggerFlag]:
    return list(
        session.scalars(
            select(ClaimTriggerFlag)
            .where(ClaimTriggerFlag.claim_trigger_id == claim_trigger_id)
            .order_by(ClaimTriggerFlag.created_at.asc(), ClaimTriggerFlag.id.asc())
        )
    )


def _get_links(session: Session, claim_trigger_id: str) -> list[ClaimTriggerLink]:
    return list(
        session.scalars(
            select(ClaimTriggerLink)
            .where(ClaimTriggerLink.claim_trigger_id == claim_trigger_id)
            .order_by(ClaimTriggerLink.created_at.asc(), ClaimTriggerLink.id.asc())
        )
    )


def _latest_payment_tracking_set(session: Session, deal_id: str) -> PaymentTrackingSet | None:
    return session.scalar(
        select(PaymentTrackingSet)
        .where(PaymentTrackingSet.deal_id == deal_id)
        .order_by(PaymentTrackingSet.created_at.desc(), PaymentTrackingSet.id.desc())
    )


def _latest_payment_tracking_record(session: Session, payment_tracking_set_id: str) -> PaymentTrackingRecord | None:
    return session.scalar(
        select(PaymentTrackingRecord)
        .where(PaymentTrackingRecord.payment_tracking_set_id == payment_tracking_set_id)
        .order_by(PaymentTrackingRecord.created_at.desc(), PaymentTrackingRecord.id.desc())
    )


def _latest_closing_docs_set(session: Session, deal_id: str) -> ClosingDocsSet | None:
    return session.scalar(
        select(ClosingDocsSet)
        .where(ClosingDocsSet.deal_id == deal_id)
        .order_by(ClosingDocsSet.created_at.desc(), ClosingDocsSet.id.desc())
    )


def _latest_incident_register_set(session: Session, deal_id: str) -> IncidentRegisterSet | None:
    return session.scalar(
        select(IncidentRegisterSet)
        .where(IncidentRegisterSet.deal_id == deal_id)
        .order_by(IncidentRegisterSet.created_at.desc(), IncidentRegisterSet.id.desc())
    )


def build_claim_trigger(session: Session, payload: BuildClaimTriggerRequest) -> ClaimTriggerSet:
    payment_set = _latest_payment_tracking_set(session, payload.deal_id)
    if not payment_set:
        raise ValidationError("Claim trigger requires canonical payment tracking")
    payment_record = _latest_payment_tracking_record(session, payment_set.payment_tracking_set_id)
    closing_docs_set = _latest_closing_docs_set(session, payload.deal_id)
    incident_set = _latest_incident_register_set(session, payload.deal_id)

    trigger_status = ClaimTriggerStatus.CLEAR
    trigger_reason = "No claim trigger condition detected."
    summary_text = "Canonical claims trigger remains clear."
    if payment_set.payment_status == PaymentTrackingStatus.OVERDUE or (payment_record and payment_record.overdue_days > 0):
        trigger_status = ClaimTriggerStatus.TRIGGERED
        trigger_reason = "Payment overdue condition detected."
        summary_text = "Claim trigger activated due to overdue payment."

    trigger_set = ClaimTriggerSet(
        claim_trigger_set_id=next_claim_trigger_set_id(session, ClaimTriggerSet.claim_trigger_set_id),
        deal_id=payload.deal_id,
        trigger_status=trigger_status,
    )
    session.add(trigger_set)
    session.flush()
    try:
        record = ClaimTriggerRecord(
            claim_trigger_id=next_claim_trigger_id(session, ClaimTriggerRecord.claim_trigger_id),
            claim_trigger_set_id=trigger_set.claim_trigger_set_id,
            summary_text=summary_text,
            trigger_reason=trigger_reason,
        )
        session.add(record)
        session.flush()
        if trigger_status == ClaimTriggerStatus.TRIGGERED:
            session.add(
                ClaimTriggerFlag(
                    claim_trigger_id=record.claim_trigger_id,
                    flag_code="PAYMENT_OVERDUE_TRIGGER",
                    severity=RiskSeverity.HIGH,
                    summary=summary_text,
                )
            )
        if closing_docs_set and str(closing_docs_set.docs_status) != "READY":
            session.add(
                ClaimTriggerFlag(
                    claim_trigger_id=record.claim_trigger_id,
                    flag_code="CLOSING_DOCS_GAP",
                    severity=RiskSeverity.MEDIUM,
                    summary="Closing docs are not fully ready for payment claim context.",
                )
            )
        links = [payment_set.payment_tracking_set_id]
        if closing_docs_set:
            links.append(closing_docs_set.closing_docs_set_id)
        if incident_set:
            links.append(incident_set.incident_register_set_id)
        for source_ref in links:
            session.add(ClaimTriggerLink(claim_trigger_id=record.claim_trigger_id, source_ref=source_ref))
        trigger_set.updated_at = utcnow()
        session.add(trigger_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="claim_trigger_built",
            source_module_id="M-044",
            severity=EventSeverity.INFO,
            payload_json={
                "claim_trigger_set_id": trigger_set.claim_trigger_set_id,
                "claim_trigger_id": record.claim_trigger_id,
                "trigger_status": str(trigger_set.trigger_status),
            },
        )
        session.commit()
    except Exception as exc:
        trigger_set.trigger_status = ClaimTriggerStatus.ESCALATED
        trigger_set.updated_at = utcnow()
        session.add(trigger_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="claim_trigger_failed",
            source_module_id="M-044",
            severity=EventSeverity.HIGH,
            payload_json={"claim_trigger_set_id": trigger_set.claim_trigger_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(trigger_set)
    return trigger_set


def get_claim_trigger_set(
    session: Session,
    claim_trigger_set_id: str,
) -> tuple[ClaimTriggerSet, list[tuple[ClaimTriggerRecord, list[ClaimTriggerFlag], list[ClaimTriggerLink]]]]:
    trigger_set = _get_set(session, claim_trigger_set_id)
    records = _get_records(session, claim_trigger_set_id)
    return trigger_set, [(record, _get_flags(session, record.claim_trigger_id), _get_links(session, record.claim_trigger_id)) for record in records]


def list_claim_trigger_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ClaimTriggerSet, list[tuple[ClaimTriggerRecord, list[ClaimTriggerFlag], list[ClaimTriggerLink]]]]]:
    query = select(ClaimTriggerSet).order_by(ClaimTriggerSet.created_at.desc(), ClaimTriggerSet.id.desc())
    if deal_id:
        query = query.where(ClaimTriggerSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_claim_trigger_set(session, item.claim_trigger_set_id) for item in sets]


def get_claim_trigger_record(
    session: Session,
    claim_trigger_id: str,
) -> tuple[ClaimTriggerRecord, list[ClaimTriggerFlag], list[ClaimTriggerLink]]:
    record = _get_record(session, claim_trigger_id)
    return record, _get_flags(session, claim_trigger_id), _get_links(session, claim_trigger_id)
