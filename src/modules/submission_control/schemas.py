from datetime import datetime

from pydantic import Field

from src.shared.enums import SubmissionAttemptStatus, SubmissionChannelType, SubmissionExecutionStatus
from src.shared.types.common import APIModel


class BuildSubmissionControlRequest(APIModel):
    deal_id: str
    submission_readiness_set_id: str
    bid_package_set_id: str


class StartSubmissionExecutionRequest(APIModel):
    submission_execution_set_id: str
    channel_type: SubmissionChannelType
    initiated_by_ref: str | None = None
    started_at: datetime | None = None


class RegisterSubmissionAttemptRequest(APIModel):
    submission_execution_id: str
    attempt_no: int = Field(gt=0)
    attempt_status: SubmissionAttemptStatus
    notes: str | None = None


class SubmissionAttemptResponse(APIModel):
    submission_attempt_id: str
    submission_execution_id: str
    attempt_no: int
    attempt_status: SubmissionAttemptStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class SubmissionExecutionRecordResponse(APIModel):
    submission_execution_id: str
    submission_execution_set_id: str
    channel_type: SubmissionChannelType
    initiated_by_ref: str | None
    started_at: datetime
    finished_at: datetime | None
    created_at: datetime
    updated_at: datetime
    attempts: list[SubmissionAttemptResponse]


class SubmissionExecutionSetResponse(APIModel):
    submission_execution_set_id: str
    deal_id: str
    submission_readiness_set_id: str
    bid_package_set_id: str
    execution_status: SubmissionExecutionStatus
    created_at: datetime
    updated_at: datetime
    records: list[SubmissionExecutionRecordResponse]
