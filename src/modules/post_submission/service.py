from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.event_log.service import append_event_record
from src.modules.post_submission.models import (
    PostSubmissionEvent,
    PostSubmissionTrackerRecord,
    PostSubmissionTrackerSet,
)
from src.modules.post_submission.schemas import (
    BuildPostSubmissionTrackerRequest,
    RegisterPostSubmissionEventRequest,
)
from src.modules.submission_control.service import get_submission_execution_set
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    PostSubmissionStage,
    PostSubmissionTrackerStatus,
    SubmissionExecutionStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import (
    next_post_submission_event_id,
    next_post_submission_tracker_id,
    next_post_submission_tracker_set_id,
)
from src.shared.validation import require_non_empty, require_same_reference

_CLOSED_STAGES = {
    str(PostSubmissionStage.AWARDED),
    str(PostSubmissionStage.LOST),
    str(PostSubmissionStage.CANCELLED),
}


def _get_set(session: Session, post_submission_tracker_set_id: str) -> PostSubmissionTrackerSet:
    record = session.scalar(
        select(PostSubmissionTrackerSet).where(
            PostSubmissionTrackerSet.post_submission_tracker_set_id == post_submission_tracker_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Post-submission tracker set '{post_submission_tracker_set_id}' was not found")
    return record


def _get_record(session: Session, post_submission_tracker_id: str) -> PostSubmissionTrackerRecord:
    record = session.scalar(
        select(PostSubmissionTrackerRecord).where(
            PostSubmissionTrackerRecord.post_submission_tracker_id == post_submission_tracker_id
        )
    )
    if not record:
        raise NotFoundError(f"Post-submission tracker record '{post_submission_tracker_id}' was not found")
    return record


def _get_records(session: Session, post_submission_tracker_set_id: str) -> list[PostSubmissionTrackerRecord]:
    return list(
        session.scalars(
            select(PostSubmissionTrackerRecord)
            .where(PostSubmissionTrackerRecord.post_submission_tracker_set_id == post_submission_tracker_set_id)
            .order_by(PostSubmissionTrackerRecord.created_at.asc(), PostSubmissionTrackerRecord.id.asc())
        )
    )


def _get_events(session: Session, post_submission_tracker_id: str) -> list[PostSubmissionEvent]:
    return list(
        session.scalars(
            select(PostSubmissionEvent)
            .where(PostSubmissionEvent.post_submission_tracker_id == post_submission_tracker_id)
            .order_by(PostSubmissionEvent.event_timestamp.asc(), PostSubmissionEvent.id.asc())
        )
    )


def build_post_submission_tracker(
    session: Session,
    payload: BuildPostSubmissionTrackerRequest,
) -> PostSubmissionTrackerSet:
    execution_set, execution_records = get_submission_execution_set(session, payload.submission_execution_set_id)
    require_same_reference(payload.deal_id, execution_set.deal_id, "deal_id")
    if str(execution_set.execution_status) != str(SubmissionExecutionStatus.SUBMITTED):
        raise ValidationError("Post-submission tracker can only be built after a SUBMITTED execution")
    if not execution_records:
        raise ValidationError("Post-submission tracker requires a persisted submission execution record")

    tracker_set = PostSubmissionTrackerSet(
        post_submission_tracker_set_id=next_post_submission_tracker_set_id(
            session, PostSubmissionTrackerSet.post_submission_tracker_set_id
        ),
        deal_id=payload.deal_id,
        submission_execution_set_id=execution_set.submission_execution_set_id,
        tracker_status=PostSubmissionTrackerStatus.ACTIVE,
    )
    session.add(tracker_set)
    session.flush()
    try:
        tracker_record = PostSubmissionTrackerRecord(
            post_submission_tracker_id=next_post_submission_tracker_id(
                session, PostSubmissionTrackerRecord.post_submission_tracker_id
            ),
            post_submission_tracker_set_id=tracker_set.post_submission_tracker_set_id,
            current_stage=payload.initial_stage,
            summary_text=payload.summary_text or "Submission executed; post-submission tracking opened.",
        )
        session.add(tracker_record)
        tracker_set.updated_at = utcnow()
        session.add(tracker_set)
        append_event_record(
            session,
            deal_id=payload.deal_id,
            event_code="post_submission_tracker_built",
            source_module_id="M-036",
            severity=EventSeverity.INFO,
            payload_json={
                "post_submission_tracker_set_id": tracker_set.post_submission_tracker_set_id,
                "post_submission_tracker_id": tracker_record.post_submission_tracker_id,
                "submission_execution_set_id": execution_set.submission_execution_set_id,
            },
        )
        session.commit()
    except Exception:
        tracker_set.tracker_status = PostSubmissionTrackerStatus.STALE
        tracker_set.updated_at = utcnow()
        session.add(tracker_set)
        session.commit()
        raise
    session.refresh(tracker_set)
    return tracker_set


def register_post_submission_event(
    session: Session,
    payload: RegisterPostSubmissionEventRequest,
) -> PostSubmissionEvent:
    tracker_record = _get_record(session, payload.post_submission_tracker_id)
    tracker_set = _get_set(session, tracker_record.post_submission_tracker_set_id)
    event = PostSubmissionEvent(
        post_submission_event_id=next_post_submission_event_id(session, PostSubmissionEvent.post_submission_event_id),
        post_submission_tracker_id=tracker_record.post_submission_tracker_id,
        event_type=payload.event_type,
        event_timestamp=payload.event_timestamp or utcnow(),
        summary=require_non_empty(payload.summary, "summary"),
        source_ref=require_non_empty(payload.source_ref, "source_ref") if payload.source_ref else None,
    )
    session.add(event)

    next_stage = payload.stage or tracker_record.current_stage
    tracker_record.current_stage = next_stage
    tracker_record.summary_text = event.summary
    tracker_record.updated_at = utcnow()
    tracker_set.updated_at = utcnow()
    if str(next_stage) in _CLOSED_STAGES:
        tracker_set.tracker_status = PostSubmissionTrackerStatus.CLOSED
    session.add(tracker_record)
    session.add(tracker_set)

    append_event_record(
        session,
        deal_id=tracker_set.deal_id,
        event_code="post_submission_event_recorded",
        source_module_id="M-036",
        severity=EventSeverity.INFO,
        payload_json={
            "post_submission_tracker_set_id": tracker_set.post_submission_tracker_set_id,
            "post_submission_tracker_id": tracker_record.post_submission_tracker_id,
            "post_submission_event_id": event.post_submission_event_id,
            "current_stage": str(next_stage),
        },
    )
    if tracker_set.tracker_status == PostSubmissionTrackerStatus.CLOSED:
        append_event_record(
            session,
            deal_id=tracker_set.deal_id,
            event_code="post_submission_tracker_closed",
            source_module_id="M-036",
            severity=EventSeverity.INFO,
            payload_json={
                "post_submission_tracker_set_id": tracker_set.post_submission_tracker_set_id,
                "post_submission_tracker_id": tracker_record.post_submission_tracker_id,
                "current_stage": str(next_stage),
            },
        )
    session.commit()
    session.refresh(event)
    return event


def get_post_submission_tracker_set(
    session: Session,
    post_submission_tracker_set_id: str,
) -> tuple[PostSubmissionTrackerSet, list[tuple[PostSubmissionTrackerRecord, list[PostSubmissionEvent]]]]:
    tracker_set = _get_set(session, post_submission_tracker_set_id)
    records = _get_records(session, post_submission_tracker_set_id)
    return tracker_set, [(record, _get_events(session, record.post_submission_tracker_id)) for record in records]


def list_post_submission_tracker_sets(
    session: Session,
    *,
    deal_id: str | None = None,
) -> list[tuple[PostSubmissionTrackerSet, list[tuple[PostSubmissionTrackerRecord, list[PostSubmissionEvent]]]]]:
    query = select(PostSubmissionTrackerSet).order_by(PostSubmissionTrackerSet.created_at.desc())
    if deal_id:
        query = query.where(PostSubmissionTrackerSet.deal_id == deal_id)
    sets = list(session.scalars(query))
    return [get_post_submission_tracker_set(session, item.post_submission_tracker_set_id) for item in sets]


def get_post_submission_tracker_record(
    session: Session,
    post_submission_tracker_id: str,
) -> tuple[PostSubmissionTrackerRecord, list[PostSubmissionEvent]]:
    record = _get_record(session, post_submission_tracker_id)
    return record, _get_events(session, post_submission_tracker_id)
