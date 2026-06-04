from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.claim_triggers.models import ClaimTriggerSet
from src.modules.deal_closure_reports.models import (
    DealClosureReportLink,
    DealClosureReportRecord,
    DealClosureReportSet,
)
from src.modules.deal_closure_reports.schemas import BuildDealClosureReportRequest
from src.modules.event_log.service import append_event_record
from src.shared.db.base import utcnow
from src.shared.enums import (
    ClaimTriggerStatus,
    ClosingDocsStatus,
    DealClosureCode,
    DealClosureReportStatus,
    EventSeverity,
    PaymentTrackingStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.final_recovery_package import load_final_recovery_context
from src.shared.ids import (
    next_deal_closure_report_id,
    next_deal_closure_report_set_id,
)


def _get_set(session: Session, deal_closure_report_set_id: str) -> DealClosureReportSet:
    record = session.scalar(
        select(DealClosureReportSet).where(
            DealClosureReportSet.deal_closure_report_set_id == deal_closure_report_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Deal closure report set '{deal_closure_report_set_id}' was not found")
    return record


def _get_record(session: Session, deal_closure_report_id: str) -> DealClosureReportRecord:
    record = session.scalar(
        select(DealClosureReportRecord).where(DealClosureReportRecord.deal_closure_report_id == deal_closure_report_id)
    )
    if not record:
        raise NotFoundError(f"Deal closure report record '{deal_closure_report_id}' was not found")
    return record


def _get_records(session: Session, deal_closure_report_set_id: str) -> list[DealClosureReportRecord]:
    return list(
        session.scalars(
            select(DealClosureReportRecord)
            .where(DealClosureReportRecord.deal_closure_report_set_id == deal_closure_report_set_id)
            .order_by(DealClosureReportRecord.created_at.asc(), DealClosureReportRecord.id.asc())
        )
    )


def _get_links(session: Session, deal_closure_report_id: str) -> list[DealClosureReportLink]:
    return list(
        session.scalars(
            select(DealClosureReportLink)
            .where(DealClosureReportLink.deal_closure_report_id == deal_closure_report_id)
            .order_by(DealClosureReportLink.created_at.asc(), DealClosureReportLink.id.asc())
        )
    )


def build_deal_closure_report(session: Session, payload: BuildDealClosureReportRequest) -> DealClosureReportSet:
    context = load_final_recovery_context(session, payload.deal_id)
    if not context.deal_closure_set or not context.deal_closure_record:
        raise ValidationError("Deal closure report requires a persisted helper deal closure")
    if not context.claim_trigger_set:
        raise ValidationError("Deal closure report requires canonical claim trigger context")

    report_status = DealClosureReportStatus.BUILT
    closure_health = "CLEAN"
    summary_parts = [
        f"Closure code: {context.deal_closure_record.closure_code}.",
        f"Claim status: {context.claim_trigger_set.trigger_status}.",
    ]
    if context.payment_tracking_set:
        summary_parts.append(f"Payment status: {context.payment_tracking_set.payment_status}.")
        if context.payment_tracking_set.payment_status == PaymentTrackingStatus.OVERDUE:
            report_status = DealClosureReportStatus.ATTENTION_REQUIRED
            closure_health = "PAYMENT_RISK"
    if context.closing_docs_set:
        summary_parts.append(f"Closing docs: {context.closing_docs_set.docs_status}.")
        if context.closing_docs_set.docs_status != ClosingDocsStatus.READY:
            report_status = DealClosureReportStatus.ATTENTION_REQUIRED
            closure_health = "DOC_GAP"
    if context.claim_trigger_set.trigger_status == ClaimTriggerStatus.TRIGGERED:
        report_status = DealClosureReportStatus.ATTENTION_REQUIRED
        closure_health = "CLAIM_TRIGGERED"
    if context.deal_closure_record.closure_code != DealClosureCode.CLOSED_WON:
        closure_health = "NON_WON"

    report_set = DealClosureReportSet(
        deal_closure_report_set_id=next_deal_closure_report_set_id(
            session, DealClosureReportSet.deal_closure_report_set_id
        ),
        deal_id=payload.deal_id,
        deal_closure_set_id=context.deal_closure_set.deal_closure_set_id,
        acceptance_control_set_id=context.acceptance_control_set.acceptance_control_set_id
        if context.acceptance_control_set
        else None,
        closing_docs_set_id=context.closing_docs_set.closing_docs_set_id if context.closing_docs_set else None,
        payment_tracking_set_id=context.payment_tracking_set.payment_tracking_set_id if context.payment_tracking_set else None,
        claim_trigger_set_id=context.claim_trigger_set.claim_trigger_set_id,
        report_status=report_status,
    )
    session.add(report_set)
    session.flush()
    try:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="deal_closure_report_set_created",
            source_module_id="M-045",
            severity=EventSeverity.INFO,
            payload_json={
                "deal_closure_report_set_id": report_set.deal_closure_report_set_id,
                "deal_closure_set_id": report_set.deal_closure_set_id,
            },
        )
        record = DealClosureReportRecord(
            deal_closure_report_id=next_deal_closure_report_id(
                session, DealClosureReportRecord.deal_closure_report_id
            ),
            deal_closure_report_set_id=report_set.deal_closure_report_set_id,
            report_code="FINAL_CLOSURE_REPORT",
            summary_text=" ".join(summary_parts),
            closure_health=closure_health,
        )
        session.add(record)
        session.flush()
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="deal_closure_report_record_created",
            source_module_id="M-045",
            severity=EventSeverity.INFO,
            payload_json={
                "deal_closure_report_set_id": report_set.deal_closure_report_set_id,
                "deal_closure_report_id": record.deal_closure_report_id,
            },
        )
        source_refs = [
            report_set.deal_closure_set_id,
            report_set.acceptance_control_set_id,
            report_set.closing_docs_set_id,
            report_set.payment_tracking_set_id,
            report_set.claim_trigger_set_id,
        ]
        for source_ref in source_refs:
            if source_ref:
                session.add(DealClosureReportLink(deal_closure_report_id=record.deal_closure_report_id, source_ref=source_ref))
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="deal_closure_report_status_changed",
            source_module_id="M-045",
            severity=EventSeverity.INFO,
            payload_json={
                "deal_closure_report_set_id": report_set.deal_closure_report_set_id,
                "report_status": str(report_set.report_status),
                "closure_health": closure_health,
            },
        )
        if report_set.report_status == DealClosureReportStatus.ATTENTION_REQUIRED:
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="deal_closure_report_trigger_detected",
                source_module_id="M-045",
                    severity=EventSeverity.WARNING,
                payload_json={
                    "deal_closure_report_set_id": report_set.deal_closure_report_set_id,
                    "claim_trigger_set_id": report_set.claim_trigger_set_id,
                    "closure_health": closure_health,
                },
            )
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="deal_closure_report_handoff_created",
            source_module_id="M-045",
            severity=EventSeverity.INFO,
            payload_json={
                "deal_closure_report_set_id": report_set.deal_closure_report_set_id,
                "downstream_module_id": "M-046",
            },
        )
        report_set.updated_at = utcnow()
        session.add(report_set)
        session.commit()
    except Exception as exc:
        session.rollback()
        failed = session.scalar(
            select(DealClosureReportSet).where(
                DealClosureReportSet.deal_closure_report_set_id == report_set.deal_closure_report_set_id
            )
        )
        if failed:
            failed.report_status = DealClosureReportStatus.FAILED
            failed.updated_at = utcnow()
            session.add(failed)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="deal_closure_report_failed",
            source_module_id="M-045",
            severity=EventSeverity.HIGH,
            payload_json={
                "deal_closure_report_set_id": report_set.deal_closure_report_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise
    session.refresh(report_set)
    return report_set


def get_deal_closure_report_set(
    session: Session,
    deal_closure_report_set_id: str,
) -> tuple[DealClosureReportSet, list[tuple[DealClosureReportRecord, list[DealClosureReportLink]]]]:
    report_set = _get_set(session, deal_closure_report_set_id)
    records = _get_records(session, deal_closure_report_set_id)
    return report_set, [(record, _get_links(session, record.deal_closure_report_id)) for record in records]


def list_deal_closure_report_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[DealClosureReportSet, list[tuple[DealClosureReportRecord, list[DealClosureReportLink]]]]]:
    query = select(DealClosureReportSet).order_by(DealClosureReportSet.created_at.desc(), DealClosureReportSet.id.desc())
    if deal_id:
        query = query.where(DealClosureReportSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_deal_closure_report_set(session, item.deal_closure_report_set_id) for item in sets]


def get_deal_closure_report_record(
    session: Session,
    deal_closure_report_id: str,
) -> tuple[DealClosureReportRecord, list[DealClosureReportLink]]:
    record = _get_record(session, deal_closure_report_id)
    return record, _get_links(session, deal_closure_report_id)
