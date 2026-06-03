from datetime import datetime

from src.shared.enums import PostSubmissionEventType, PostSubmissionStage, PostSubmissionTrackerStatus
from src.shared.types.common import APIModel


class BuildPostSubmissionTrackerRequest(APIModel):
    deal_id: str
    submission_execution_set_id: str
    initial_stage: PostSubmissionStage = PostSubmissionStage.SUBMITTED
    summary_text: str | None = None


class RegisterPostSubmissionEventRequest(APIModel):
    post_submission_tracker_id: str
    event_type: PostSubmissionEventType
    event_timestamp: datetime | None = None
    summary: str
    source_ref: str | None = None
    stage: PostSubmissionStage | None = None


class PostSubmissionEventResponse(APIModel):
    post_submission_event_id: str
    post_submission_tracker_id: str
    event_type: PostSubmissionEventType
    event_timestamp: datetime
    summary: str
    source_ref: str | None
    created_at: datetime


class PostSubmissionTrackerRecordResponse(APIModel):
    post_submission_tracker_id: str
    post_submission_tracker_set_id: str
    current_stage: PostSubmissionStage
    summary_text: str
    created_at: datetime
    updated_at: datetime
    events: list[PostSubmissionEventResponse]


class PostSubmissionTrackerSetResponse(APIModel):
    post_submission_tracker_set_id: str
    deal_id: str
    submission_execution_set_id: str
    tracker_status: PostSubmissionTrackerStatus
    created_at: datetime
    updated_at: datetime
    records: list[PostSubmissionTrackerRecordResponse]
