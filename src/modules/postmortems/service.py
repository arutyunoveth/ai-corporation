from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.incident_register.models import IncidentRegisterFlag, IncidentRegisterRecord
from src.modules.postmortems.models import (
    PostmortemActionItem,
    PostmortemFinding,
    PostmortemRecord,
    PostmortemSet,
)
from src.modules.postmortems.schemas import BuildPostmortemRequest
from src.modules.deal_closure_reports.models import DealClosureReportSet
from src.shared.db.base import utcnow
from src.shared.enums import (
    ClaimTriggerStatus,
    EventSeverity,
    PostmortemActionStatus,
    PostmortemStatus,
    RiskSeverity,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.final_recovery_package import load_final_recovery_context
from src.shared.ids import next_postmortem_id, next_postmortem_set_id


def _get_set(session: Session, postmortem_set_id: str) -> PostmortemSet:
    record = session.scalar(select(PostmortemSet).where(PostmortemSet.postmortem_set_id == postmortem_set_id))
    if not record:
        raise NotFoundError(f"Postmortem set '{postmortem_set_id}' was not found")
    return record


def _get_record(session: Session, postmortem_id: str) -> PostmortemRecord:
    record = session.scalar(select(PostmortemRecord).where(PostmortemRecord.postmortem_id == postmortem_id))
    if not record:
        raise NotFoundError(f"Postmortem record '{postmortem_id}' was not found")
    return record


def _get_records(session: Session, postmortem_set_id: str) -> list[PostmortemRecord]:
    return list(
        session.scalars(
            select(PostmortemRecord)
            .where(PostmortemRecord.postmortem_set_id == postmortem_set_id)
            .order_by(PostmortemRecord.created_at.asc(), PostmortemRecord.id.asc())
        )
    )


def _get_findings(session: Session, postmortem_id: str) -> list[PostmortemFinding]:
    return list(
        session.scalars(
            select(PostmortemFinding)
            .where(PostmortemFinding.postmortem_id == postmortem_id)
            .order_by(PostmortemFinding.created_at.asc(), PostmortemFinding.id.asc())
        )
    )


def _get_action_items(session: Session, postmortem_id: str) -> list[PostmortemActionItem]:
    return list(
        session.scalars(
            select(PostmortemActionItem)
            .where(PostmortemActionItem.postmortem_id == postmortem_id)
            .order_by(PostmortemActionItem.created_at.asc(), PostmortemActionItem.id.asc())
        )
    )


def build_postmortem(session: Session, payload: BuildPostmortemRequest) -> PostmortemSet:
    context = load_final_recovery_context(session, payload.deal_id)
    closure_report_set = session.scalar(
        select(DealClosureReportSet)
        .where(DealClosureReportSet.deal_id == payload.deal_id)
        .order_by(DealClosureReportSet.created_at.desc(), DealClosureReportSet.id.desc())
    )
    if not closure_report_set:
        raise ValidationError("Postmortem requires canonical deal closure report")

    incident_count = 0
    if context.incident_register_set:
        incident_count = int(
            session.scalar(
                select(func.count(IncidentRegisterRecord.id)).where(
                    IncidentRegisterRecord.incident_register_set_id == context.incident_register_set.incident_register_set_id
                )
            )
            or 0
        )
    flag_count = 0
    if context.incident_register_record:
        flag_count = int(
            session.scalar(
                select(func.count(IncidentRegisterFlag.id)).where(
                    IncidentRegisterFlag.incident_register_id == context.incident_register_record.incident_register_id
                )
            )
            or 0
        )
    postmortem_status = PostmortemStatus.BUILT
    root_cause_summary = "Execution completed with stable delivery and payment flow."
    if context.claim_trigger_set and context.claim_trigger_set.trigger_status == ClaimTriggerStatus.TRIGGERED:
        root_cause_summary = "Late-stage payment or claims risk was observed during closure."
        postmortem_status = PostmortemStatus.ACTIONS_DEFINED
    elif incident_count > 0 or flag_count > 0:
        root_cause_summary = "Operational incidents or flags were observed during execution."
        postmortem_status = PostmortemStatus.ACTIONS_DEFINED

    postmortem_set = PostmortemSet(
        postmortem_set_id=next_postmortem_set_id(session, PostmortemSet.postmortem_set_id),
        deal_id=payload.deal_id,
        deal_closure_report_set_id=closure_report_set.deal_closure_report_set_id,
        incident_register_set_id=context.incident_register_set.incident_register_set_id if context.incident_register_set else None,
        claim_trigger_set_id=context.claim_trigger_set.claim_trigger_set_id if context.claim_trigger_set else None,
        kpi_learning_set_id=context.kpi_learning_set.kpi_learning_set_id if context.kpi_learning_set else None,
        postmortem_status=postmortem_status,
    )
    session.add(postmortem_set)
    session.flush()
    try:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="postmortem_set_created",
            source_module_id="M-046",
            severity=EventSeverity.INFO,
            payload_json={"postmortem_set_id": postmortem_set.postmortem_set_id},
        )
        record = PostmortemRecord(
            postmortem_id=next_postmortem_id(session, PostmortemRecord.postmortem_id),
            postmortem_set_id=postmortem_set.postmortem_set_id,
            summary_text=(
                f"Postmortem for {payload.deal_id}: incidents={incident_count}, "
                f"claim_status={context.claim_trigger_set.trigger_status if context.claim_trigger_set else 'NONE'}."
            ),
            root_cause_summary=root_cause_summary,
            recommendation_summary="Convert closure observations into supplier and knowledge follow-up artifacts.",
        )
        session.add(record)
        session.flush()
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="postmortem_record_created",
            source_module_id="M-046",
            severity=EventSeverity.INFO,
            payload_json={"postmortem_set_id": postmortem_set.postmortem_set_id, "postmortem_id": record.postmortem_id},
        )
        findings: list[tuple[str, RiskSeverity, str]] = []
        if incident_count > 0:
            findings.append(("INCIDENT_PATTERN", RiskSeverity.MEDIUM, "Execution recorded operational incident signals."))
        if context.claim_trigger_set and context.claim_trigger_set.trigger_status == ClaimTriggerStatus.TRIGGERED:
            findings.append(("CLAIM_EXPOSURE", RiskSeverity.HIGH, "Claim trigger reached active state before final closure."))
        if context.kpi_learning_record and context.kpi_learning_record.margin_estimate is not None and context.kpi_learning_record.margin_estimate < 0:
            findings.append(("NEGATIVE_MARGIN", RiskSeverity.HIGH, "Estimated margin turned negative at closure time."))
        if not findings:
            findings.append(("STABLE_EXECUTION", RiskSeverity.LOW, "No critical closure exception was detected."))
        for finding_code, severity, summary in findings:
            session.add(
                PostmortemFinding(
                    postmortem_id=record.postmortem_id,
                    finding_code=finding_code,
                    severity=severity,
                    summary=summary,
                )
            )
        actions = [
            ("UPDATE_SUPPLIER_RATING", "PROCUREMENT_OWNER", "Reflect execution outcome in supplier scorecard."),
            ("CAPTURE_KNOWLEDGE", "OPS_OWNER", "Persist reusable closure lesson and artifact references."),
        ]
        if findings:
            for action_code, owner_hint, summary in actions:
                session.add(
                    PostmortemActionItem(
                        postmortem_id=record.postmortem_id,
                        action_code=action_code,
                        owner_hint=owner_hint,
                        summary=summary,
                        action_status=PostmortemActionStatus.PLANNED,
                    )
                )
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="postmortem_status_changed",
            source_module_id="M-046",
            severity=EventSeverity.INFO,
            payload_json={
                "postmortem_set_id": postmortem_set.postmortem_set_id,
                "postmortem_status": str(postmortem_set.postmortem_status),
            },
        )
        if any(severity in {RiskSeverity.HIGH, RiskSeverity.CRITICAL} for _, severity, _ in findings):
            append_event_record(
                session,
                deal_id=payload.deal_id,
                event_code="postmortem_risk_detected",
                source_module_id="M-046",
                severity=EventSeverity.WARNING,
                payload_json={"postmortem_set_id": postmortem_set.postmortem_set_id},
            )
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="postmortem_handoff_created",
            source_module_id="M-046",
            severity=EventSeverity.INFO,
            payload_json={"postmortem_set_id": postmortem_set.postmortem_set_id, "downstream_module_ids": ["M-047", "M-048"]},
        )
        postmortem_set.updated_at = utcnow()
        session.add(postmortem_set)
        session.commit()
    except Exception as exc:
        session.rollback()
        failed = session.scalar(select(PostmortemSet).where(PostmortemSet.postmortem_set_id == postmortem_set.postmortem_set_id))
        if failed:
            failed.postmortem_status = PostmortemStatus.FAILED
            failed.updated_at = utcnow()
            session.add(failed)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="postmortem_failed",
            source_module_id="M-046",
            severity=EventSeverity.HIGH,
            payload_json={"postmortem_set_id": postmortem_set.postmortem_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(postmortem_set)
    return postmortem_set


def get_postmortem_set(
    session: Session,
    postmortem_set_id: str,
) -> tuple[PostmortemSet, list[tuple[PostmortemRecord, list[PostmortemFinding], list[PostmortemActionItem]]]]:
    postmortem_set = _get_set(session, postmortem_set_id)
    records = _get_records(session, postmortem_set_id)
    return postmortem_set, [
        (record, _get_findings(session, record.postmortem_id), _get_action_items(session, record.postmortem_id))
        for record in records
    ]


def list_postmortem_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[PostmortemSet, list[tuple[PostmortemRecord, list[PostmortemFinding], list[PostmortemActionItem]]]]]:
    query = select(PostmortemSet).order_by(PostmortemSet.created_at.desc(), PostmortemSet.id.desc())
    if deal_id:
        query = query.where(PostmortemSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_postmortem_set(session, item.postmortem_set_id) for item in sets]


def get_postmortem_record(
    session: Session,
    postmortem_id: str,
) -> tuple[PostmortemRecord, list[PostmortemFinding], list[PostmortemActionItem]]:
    record = _get_record(session, postmortem_id)
    return record, _get_findings(session, postmortem_id), _get_action_items(session, postmortem_id)
