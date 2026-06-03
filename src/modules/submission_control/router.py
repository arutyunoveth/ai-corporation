from fastapi import APIRouter, Query, status

from src.modules.submission_control.schemas import (
    BuildSubmissionControlRequest,
    RegisterSubmissionAttemptRequest,
    StartSubmissionExecutionRequest,
    SubmissionAttemptResponse,
    SubmissionExecutionRecordResponse,
    SubmissionExecutionSetResponse,
)
from src.modules.submission_control.service import (
    build_submission_control,
    get_submission_execution_record,
    get_submission_execution_set,
    list_submission_execution_sets,
    record_submission_attempt,
    start_submission_execution,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["submission-control"])


def _to_attempt_response(item) -> SubmissionAttemptResponse:
    return SubmissionAttemptResponse.model_validate(item)


def _to_record_response(result: tuple) -> SubmissionExecutionRecordResponse:
    record, attempts = result
    return SubmissionExecutionRecordResponse(
        submission_execution_id=record.submission_execution_id,
        submission_execution_set_id=record.submission_execution_set_id,
        channel_type=record.channel_type,
        initiated_by_ref=record.initiated_by_ref,
        started_at=record.started_at,
        finished_at=record.finished_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        attempts=[_to_attempt_response(item) for item in attempts],
    )


def _to_set_response(result: tuple) -> SubmissionExecutionSetResponse:
    execution_set, records = result
    return SubmissionExecutionSetResponse(
        submission_execution_set_id=execution_set.submission_execution_set_id,
        deal_id=execution_set.deal_id,
        submission_readiness_set_id=execution_set.submission_readiness_set_id,
        bid_package_set_id=execution_set.bid_package_set_id,
        execution_status=execution_set.execution_status,
        created_at=execution_set.created_at,
        updated_at=execution_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post(
    "/submission-control/build",
    response_model=SubmissionExecutionSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def build_submission_control_route(
    payload: BuildSubmissionControlRequest,
    session: DBSession,
) -> SubmissionExecutionSetResponse:
    execution_set = build_submission_control(session, payload)
    return _to_set_response(get_submission_execution_set(session, execution_set.submission_execution_set_id))


@router.post(
    "/submission-control/start",
    response_model=SubmissionExecutionRecordResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_submission_execution_route(
    payload: StartSubmissionExecutionRequest,
    session: DBSession,
) -> SubmissionExecutionRecordResponse:
    record = start_submission_execution(session, payload)
    return _to_record_response(get_submission_execution_record(session, record.submission_execution_id))


@router.post(
    "/submission-control/attempts",
    response_model=SubmissionAttemptResponse,
    status_code=status.HTTP_201_CREATED,
)
def record_submission_attempt_route(
    payload: RegisterSubmissionAttemptRequest,
    session: DBSession,
) -> SubmissionAttemptResponse:
    return _to_attempt_response(record_submission_attempt(session, payload))


@router.get("/submission-control/{submission_execution_set_id}", response_model=SubmissionExecutionSetResponse)
def get_submission_execution_set_route(
    submission_execution_set_id: str,
    session: DBSession,
) -> SubmissionExecutionSetResponse:
    return _to_set_response(get_submission_execution_set(session, submission_execution_set_id))


@router.get("/submission-control", response_model=list[SubmissionExecutionSetResponse])
def list_submission_execution_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SubmissionExecutionSetResponse]:
    return [_to_set_response(item) for item in list_submission_execution_sets(session, deal_id=deal_id)]


@router.get("/submission-control/records/{submission_execution_id}", response_model=SubmissionExecutionRecordResponse)
def get_submission_execution_record_route(
    submission_execution_id: str,
    session: DBSession,
) -> SubmissionExecutionRecordResponse:
    return _to_record_response(get_submission_execution_record(session, submission_execution_id))
