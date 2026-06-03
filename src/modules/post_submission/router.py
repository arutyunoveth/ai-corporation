from fastapi import APIRouter, Query, status

from src.modules.post_submission.schemas import (
    BuildPostSubmissionTrackerRequest,
    PostSubmissionEventResponse,
    PostSubmissionTrackerRecordResponse,
    PostSubmissionTrackerSetResponse,
    RegisterPostSubmissionEventRequest,
)
from src.modules.post_submission.service import (
    build_post_submission_tracker,
    get_post_submission_tracker_record,
    get_post_submission_tracker_set,
    list_post_submission_tracker_sets,
    register_post_submission_event,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["post-submission"])


def _to_event_response(item) -> PostSubmissionEventResponse:
    return PostSubmissionEventResponse.model_validate(item)


def _to_record_response(result: tuple) -> PostSubmissionTrackerRecordResponse:
    record, events = result
    return PostSubmissionTrackerRecordResponse(
        post_submission_tracker_id=record.post_submission_tracker_id,
        post_submission_tracker_set_id=record.post_submission_tracker_set_id,
        current_stage=record.current_stage,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        events=[_to_event_response(item) for item in events],
    )


def _to_set_response(result: tuple) -> PostSubmissionTrackerSetResponse:
    tracker_set, records = result
    return PostSubmissionTrackerSetResponse(
        post_submission_tracker_set_id=tracker_set.post_submission_tracker_set_id,
        deal_id=tracker_set.deal_id,
        submission_execution_set_id=tracker_set.submission_execution_set_id,
        tracker_status=tracker_set.tracker_status,
        created_at=tracker_set.created_at,
        updated_at=tracker_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/post-submission/build", response_model=PostSubmissionTrackerSetResponse, status_code=status.HTTP_201_CREATED)
def build_post_submission_tracker_route(
    payload: BuildPostSubmissionTrackerRequest,
    session: DBSession,
) -> PostSubmissionTrackerSetResponse:
    tracker_set = build_post_submission_tracker(session, payload)
    return _to_set_response(get_post_submission_tracker_set(session, tracker_set.post_submission_tracker_set_id))


@router.post("/post-submission/events", response_model=PostSubmissionEventResponse, status_code=status.HTTP_201_CREATED)
def register_post_submission_event_route(
    payload: RegisterPostSubmissionEventRequest,
    session: DBSession,
) -> PostSubmissionEventResponse:
    return _to_event_response(register_post_submission_event(session, payload))


@router.get("/post-submission/{post_submission_tracker_set_id}", response_model=PostSubmissionTrackerSetResponse)
def get_post_submission_tracker_set_route(
    post_submission_tracker_set_id: str,
    session: DBSession,
) -> PostSubmissionTrackerSetResponse:
    return _to_set_response(get_post_submission_tracker_set(session, post_submission_tracker_set_id))


@router.get("/post-submission", response_model=list[PostSubmissionTrackerSetResponse])
def list_post_submission_tracker_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[PostSubmissionTrackerSetResponse]:
    return [_to_set_response(item) for item in list_post_submission_tracker_sets(session, deal_id=deal_id)]


@router.get("/post-submission/records/{post_submission_tracker_id}", response_model=PostSubmissionTrackerRecordResponse)
def get_post_submission_tracker_record_route(
    post_submission_tracker_id: str,
    session: DBSession,
) -> PostSubmissionTrackerRecordResponse:
    return _to_record_response(get_post_submission_tracker_record(session, post_submission_tracker_id))
