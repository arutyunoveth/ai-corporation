from fastapi import APIRouter, Query, status

from src.modules.submission_readiness.schemas import (
    BuildSubmissionReadinessRequest,
    SubmissionReadinessFlagResponse,
    SubmissionReadinessRecordResponse,
    SubmissionReadinessSetResponse,
)
from src.modules.submission_readiness.service import (
    build_submission_readiness,
    get_submission_readiness_record,
    get_submission_readiness_set,
    list_submission_readiness_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["submission-readiness"])


def _to_record_response(result: tuple) -> SubmissionReadinessRecordResponse:
    record, flags = result
    return SubmissionReadinessRecordResponse(
        submission_readiness_id=record.submission_readiness_id,
        submission_readiness_set_id=record.submission_readiness_set_id,
        recommendation=record.recommendation,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        flags=[SubmissionReadinessFlagResponse.model_validate(item) for item in flags],
    )


def _to_set_response(result: tuple) -> SubmissionReadinessSetResponse:
    readiness_set, records = result
    return SubmissionReadinessSetResponse(
        submission_readiness_set_id=readiness_set.submission_readiness_set_id,
        deal_id=readiness_set.deal_id,
        bid_completeness_set_id=readiness_set.bid_completeness_set_id,
        ceo_approval_set_id=readiness_set.ceo_approval_set_id,
        finance_memo_set_id=readiness_set.finance_memo_set_id,
        integrated_risk_memo_set_id=readiness_set.integrated_risk_memo_set_id,
        readiness_status=readiness_set.readiness_status,
        created_at=readiness_set.created_at,
        updated_at=readiness_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post(
    "/submission-readiness/build",
    response_model=SubmissionReadinessSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def build_submission_readiness_route(
    payload: BuildSubmissionReadinessRequest,
    session: DBSession,
) -> SubmissionReadinessSetResponse:
    readiness_set = build_submission_readiness(session, payload)
    return _to_set_response(get_submission_readiness_set(session, readiness_set.submission_readiness_set_id))


@router.get("/submission-readiness/{submission_readiness_set_id}", response_model=SubmissionReadinessSetResponse)
def get_submission_readiness_set_route(
    submission_readiness_set_id: str,
    session: DBSession,
) -> SubmissionReadinessSetResponse:
    return _to_set_response(get_submission_readiness_set(session, submission_readiness_set_id))


@router.get("/submission-readiness", response_model=list[SubmissionReadinessSetResponse])
def list_submission_readiness_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SubmissionReadinessSetResponse]:
    return [_to_set_response(item) for item in list_submission_readiness_sets(session, deal_id=deal_id)]


@router.get(
    "/submission-readiness/records/{submission_readiness_id}",
    response_model=SubmissionReadinessRecordResponse,
)
def get_submission_readiness_record_route(
    submission_readiness_id: str,
    session: DBSession,
) -> SubmissionReadinessRecordResponse:
    return _to_record_response(get_submission_readiness_record(session, submission_readiness_id))
