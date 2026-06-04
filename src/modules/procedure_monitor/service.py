from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.outcome_intake.models import OutcomeIntakeRecord, OutcomeIntakeSet
from src.modules.post_submission.models import PostSubmissionEvent, PostSubmissionTrackerRecord, PostSubmissionTrackerSet
from src.modules.procedure_monitor.models import (
    ProcedureMonitorAlert,
    ProcedureMonitorEvent,
    ProcedureMonitorRecord,
    ProcedureMonitorSet,
)
from src.modules.procedure_monitor.schemas import (
    BuildProcedureMonitorRequest,
    RegisterProcedureMonitorEventRequest,
)
from src.modules.submission_control.models import SubmissionExecutionSet
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    OutcomeCode,
    PostSubmissionStage,
    ProcedureStatus,
    RiskSeverity,
    SubmissionExecutionStatus,
)
from src.shared.enums.recovery_r2 import ProcedureMonitorEventType
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_procedure_event_id,
    next_procedure_monitor_id,
    next_procedure_monitor_set_id,
)
from src.shared.validation import require_non_empty


def _get_set(session: Session, procedure_monitor_set_id: str) -> ProcedureMonitorSet:
    record = session.scalar(
        select(ProcedureMonitorSet).where(ProcedureMonitorSet.procedure_monitor_set_id == procedure_monitor_set_id)
    )
    if not record:
        raise NotFoundError(f"Procedure monitor set '{procedure_monitor_set_id}' was not found")
    return record


def _get_record(session: Session, procedure_monitor_id: str) -> ProcedureMonitorRecord:
    record = session.scalar(
        select(ProcedureMonitorRecord).where(ProcedureMonitorRecord.procedure_monitor_id == procedure_monitor_id)
    )
    if not record:
        raise NotFoundError(f"Procedure monitor record '{procedure_monitor_id}' was not found")
    return record


def _get_records(session: Session, procedure_monitor_set_id: str) -> list[ProcedureMonitorRecord]:
    return list(
        session.scalars(
            select(ProcedureMonitorRecord)
            .where(ProcedureMonitorRecord.procedure_monitor_set_id == procedure_monitor_set_id)
            .order_by(ProcedureMonitorRecord.created_at.asc(), ProcedureMonitorRecord.id.asc())
        )
    )


def _get_events(session: Session, procedure_monitor_id: str) -> list[ProcedureMonitorEvent]:
    return list(
        session.scalars(
            select(ProcedureMonitorEvent)
            .where(ProcedureMonitorEvent.procedure_monitor_id == procedure_monitor_id)
            .order_by(ProcedureMonitorEvent.event_timestamp.asc(), ProcedureMonitorEvent.id.asc())
        )
    )


def _get_alerts(session: Session, procedure_monitor_id: str) -> list[ProcedureMonitorAlert]:
    return list(
        session.scalars(
            select(ProcedureMonitorAlert)
            .where(ProcedureMonitorAlert.procedure_monitor_id == procedure_monitor_id)
            .order_by(ProcedureMonitorAlert.created_at.asc(), ProcedureMonitorAlert.id.asc())
        )
    )


def _latest_submitted_execution_set(session: Session, deal_id: str) -> SubmissionExecutionSet:
    execution_set = session.scalar(
        select(SubmissionExecutionSet)
        .where(
            SubmissionExecutionSet.deal_id == deal_id,
            SubmissionExecutionSet.execution_status == SubmissionExecutionStatus.SUBMITTED,
        )
        .order_by(SubmissionExecutionSet.created_at.desc(), SubmissionExecutionSet.id.desc())
        .limit(1)
    )
    if not execution_set:
        raise ValidationError("Procedure monitor requires a SUBMITTED execution context")
    return execution_set


def _latest_tracker_context(
    session: Session, deal_id: str
) -> tuple[PostSubmissionTrackerSet | None, PostSubmissionTrackerRecord | None, list[PostSubmissionEvent]]:
    tracker_set = session.scalar(
        select(PostSubmissionTrackerSet)
        .where(PostSubmissionTrackerSet.deal_id == deal_id)
        .order_by(PostSubmissionTrackerSet.created_at.desc(), PostSubmissionTrackerSet.id.desc())
        .limit(1)
    )
    if not tracker_set:
        return None, None, []
    tracker_record = session.scalar(
        select(PostSubmissionTrackerRecord)
        .where(PostSubmissionTrackerRecord.post_submission_tracker_set_id == tracker_set.post_submission_tracker_set_id)
        .order_by(PostSubmissionTrackerRecord.created_at.desc(), PostSubmissionTrackerRecord.id.desc())
        .limit(1)
    )
    if not tracker_record:
        return tracker_set, None, []
    events = list(
        session.scalars(
            select(PostSubmissionEvent)
            .where(PostSubmissionEvent.post_submission_tracker_id == tracker_record.post_submission_tracker_id)
            .order_by(PostSubmissionEvent.event_timestamp.asc(), PostSubmissionEvent.id.asc())
        )
    )
    return tracker_set, tracker_record, events


def _latest_outcome_context(
    session: Session, deal_id: str
) -> tuple[OutcomeIntakeSet | None, OutcomeIntakeRecord | None]:
    outcome_set = session.scalar(
        select(OutcomeIntakeSet)
        .where(OutcomeIntakeSet.deal_id == deal_id)
        .order_by(OutcomeIntakeSet.created_at.desc(), OutcomeIntakeSet.id.desc())
        .limit(1)
    )
    if not outcome_set:
        return None, None
    outcome_record = session.scalar(
        select(OutcomeIntakeRecord)
        .where(OutcomeIntakeRecord.outcome_intake_set_id == outcome_set.outcome_intake_set_id)
        .order_by(OutcomeIntakeRecord.effective_at.desc(), OutcomeIntakeRecord.id.desc())
        .limit(1)
    )
    return outcome_set, outcome_record


def _derive_procedure_status(outcome_record: OutcomeIntakeRecord | None) -> ProcedureStatus:
    if not outcome_record:
        return ProcedureStatus.BID_IN_PROGRESS
    if outcome_record.outcome_code == OutcomeCode.WON:
        return ProcedureStatus.WON_PENDING_CONTRACT
    if outcome_record.outcome_code in {OutcomeCode.LOST, OutcomeCode.REJECTED}:
        return ProcedureStatus.LOST
    if outcome_record.outcome_code == OutcomeCode.CANCELLED:
        return ProcedureStatus.CANCELLED
    return ProcedureStatus.BID_IN_PROGRESS


def _build_alert_specs(
    *,
    tracker_record: PostSubmissionTrackerRecord | None,
    outcome_record: OutcomeIntakeRecord | None,
) -> list[dict]:
    alerts: list[dict] = []
    if outcome_record is None:
        alerts.append(
            {
                "alert_code": "OUTCOME_PENDING",
                "severity": RiskSeverity.MEDIUM,
                "summary": "Tender procedure still has no explicit final outcome context.",
            }
        )
    if tracker_record and tracker_record.current_stage == PostSubmissionStage.CLARIFICATION:
        alerts.append(
            {
                "alert_code": "CLARIFICATION_OPEN",
                "severity": RiskSeverity.MEDIUM,
                "summary": "Procedure is currently in clarification stage and needs follow-up.",
            }
        )
    if outcome_record and outcome_record.outcome_code == OutcomeCode.WON:
        alerts.append(
            {
                "alert_code": "CONTRACT_NEGOTIATION_OPEN",
                "severity": RiskSeverity.LOW,
                "summary": "Winning outcome recorded; contract negotiation workspace should be opened.",
            }
        )
    return alerts


def build_procedure_monitor(session: Session, payload: BuildProcedureMonitorRequest) -> ProcedureMonitorSet:
    _latest_submitted_execution_set(session, payload.deal_id)
    tracker_set, tracker_record, tracker_events = _latest_tracker_context(session, payload.deal_id)
    outcome_set, outcome_record = _latest_outcome_context(session, payload.deal_id)

    procedure_set = ProcedureMonitorSet(
        procedure_monitor_set_id=next_procedure_monitor_set_id(
            session, ProcedureMonitorSet.procedure_monitor_set_id
        ),
        deal_id=payload.deal_id,
        procedure_status=_derive_procedure_status(outcome_record),
    )
    session.add(procedure_set)
    session.flush()
    try:
        current_stage = (
            tracker_record.current_stage
            if tracker_record
            else PostSubmissionStage.SUBMITTED
        )
        summary_text = (
            outcome_record.rationale
            if outcome_record
            else tracker_record.summary_text
            if tracker_record
            else "Submission is in progress; procedure monitor opened."
        )
        record = ProcedureMonitorRecord(
            procedure_monitor_id=next_procedure_monitor_id(session, ProcedureMonitorRecord.procedure_monitor_id),
            procedure_monitor_set_id=procedure_set.procedure_monitor_set_id,
            current_stage=str(current_stage),
            summary_text=summary_text,
        )
        session.add(record)
        session.flush()
        for tracker_event in tracker_events:
            session.add(
                ProcedureMonitorEvent(
                    procedure_event_id=next_procedure_event_id(
                        session, ProcedureMonitorEvent.procedure_event_id
                    ),
                    procedure_monitor_id=record.procedure_monitor_id,
                    event_type=ProcedureMonitorEventType.STATUS_UPDATE,
                    event_timestamp=tracker_event.event_timestamp,
                    summary=tracker_event.summary,
                    source_ref=tracker_event.source_ref,
                )
            )
            session.flush()
        if outcome_record:
            session.add(
                ProcedureMonitorEvent(
                    procedure_event_id=next_procedure_event_id(session, ProcedureMonitorEvent.procedure_event_id),
                    procedure_monitor_id=record.procedure_monitor_id,
                    event_type=ProcedureMonitorEventType.OUTCOME,
                    event_timestamp=outcome_record.effective_at,
                    summary=outcome_record.rationale,
                    source_ref=outcome_set.outcome_intake_set_id if outcome_set else None,
                )
            )
            session.flush()
        for alert_spec in _build_alert_specs(tracker_record=tracker_record, outcome_record=outcome_record):
            session.add(ProcedureMonitorAlert(procedure_monitor_id=record.procedure_monitor_id, **alert_spec))
        procedure_set.updated_at = utcnow()
        session.add(procedure_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="procedure_monitor_built",
            source_module_id="M-033",
            severity=EventSeverity.INFO,
            payload_json={
                "procedure_monitor_set_id": procedure_set.procedure_monitor_set_id,
                "procedure_monitor_id": record.procedure_monitor_id,
                "tracker_set_id": tracker_set.post_submission_tracker_set_id if tracker_set else None,
                "outcome_set_id": outcome_set.outcome_intake_set_id if outcome_set else None,
            },
        )
        session.commit()
    except Exception as exc:
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="procedure_monitor_failed",
            source_module_id="M-033",
            severity=EventSeverity.HIGH,
            payload_json={"procedure_monitor_set_id": procedure_set.procedure_monitor_set_id, "error": str(exc)},
        )
        session.commit()
        raise
    session.refresh(procedure_set)
    return procedure_set


def register_procedure_monitor_event(
    session: Session, payload: RegisterProcedureMonitorEventRequest
) -> ProcedureMonitorEvent:
    record = _get_record(session, payload.procedure_monitor_id)
    monitor_set = _get_set(session, record.procedure_monitor_set_id)
    event = ProcedureMonitorEvent(
        procedure_event_id=next_procedure_event_id(session, ProcedureMonitorEvent.procedure_event_id),
        procedure_monitor_id=record.procedure_monitor_id,
        event_type=payload.event_type,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=payload.source_ref.strip() if payload.source_ref else None,
    )
    session.add(event)
    record.summary_text = event.summary
    if payload.current_stage:
        record.current_stage = payload.current_stage.strip()
    record.updated_at = utcnow()
    if record.current_stage in {PostSubmissionStage.AWARDED, "WON_PENDING_CONTRACT"}:
        monitor_set.procedure_status = ProcedureStatus.WON_PENDING_CONTRACT
    elif record.current_stage == PostSubmissionStage.LOST:
        monitor_set.procedure_status = ProcedureStatus.LOST
    elif record.current_stage == PostSubmissionStage.CANCELLED:
        monitor_set.procedure_status = ProcedureStatus.CANCELLED
    else:
        monitor_set.procedure_status = ProcedureStatus.BID_IN_PROGRESS
    monitor_set.updated_at = utcnow()
    session.add(record)
    session.add(monitor_set)
    if event.event_type == ProcedureMonitorEventType.ALERT:
        session.add(
            ProcedureMonitorAlert(
                procedure_monitor_id=record.procedure_monitor_id,
                alert_code="MANUAL_ALERT",
                severity=RiskSeverity.MEDIUM,
                summary=event.summary,
            )
        )
    append_event_record(
        session,
        deal_id=monitor_set.deal_id,
        event_code="procedure_monitor_event_recorded",
        source_module_id="M-033",
        severity=EventSeverity.INFO,
        payload_json={
            "procedure_monitor_set_id": monitor_set.procedure_monitor_set_id,
            "procedure_monitor_id": record.procedure_monitor_id,
            "procedure_event_id": event.procedure_event_id,
            "procedure_status": str(monitor_set.procedure_status),
        },
    )
    session.commit()
    session.refresh(event)
    return event


def get_procedure_monitor_set(
    session: Session,
    procedure_monitor_set_id: str,
) -> tuple[ProcedureMonitorSet, list[tuple[ProcedureMonitorRecord, list[ProcedureMonitorEvent], list[ProcedureMonitorAlert]]]]:
    monitor_set = _get_set(session, procedure_monitor_set_id)
    records = _get_records(session, procedure_monitor_set_id)
    return monitor_set, [
        (record, _get_events(session, record.procedure_monitor_id), _get_alerts(session, record.procedure_monitor_id))
        for record in records
    ]


def list_procedure_monitor_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[ProcedureMonitorSet, list[tuple[ProcedureMonitorRecord, list[ProcedureMonitorEvent], list[ProcedureMonitorAlert]]]]]:
    query = select(ProcedureMonitorSet).order_by(ProcedureMonitorSet.created_at.desc(), ProcedureMonitorSet.id.desc())
    if deal_id:
        query = query.where(ProcedureMonitorSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_procedure_monitor_set(session, item.procedure_monitor_set_id) for item in sets]


def get_procedure_monitor_record(
    session: Session,
    procedure_monitor_id: str,
) -> tuple[ProcedureMonitorRecord, list[ProcedureMonitorEvent], list[ProcedureMonitorAlert]]:
    record = _get_record(session, procedure_monitor_id)
    return record, _get_events(session, procedure_monitor_id), _get_alerts(session, procedure_monitor_id)
