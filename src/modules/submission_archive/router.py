from fastapi import APIRouter, Query, status

from src.modules.submission_archive.schemas import (
    BuildSubmissionArchiveRequest,
    SubmissionArchiveItemResponse,
    SubmissionArchiveRecordResponse,
    SubmissionArchiveSetResponse,
)
from src.modules.submission_archive.service import (
    build_submission_archive,
    get_submission_archive_record,
    get_submission_archive_set,
    list_submission_archive_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["submission-archive"])


def _to_record_response(result: tuple) -> SubmissionArchiveRecordResponse:
    record, items = result
    return SubmissionArchiveRecordResponse(
        submission_archive_id=record.submission_archive_id,
        submission_archive_set_id=record.submission_archive_set_id,
        archive_manifest_json=record.archive_manifest_json,
        proof_summary=record.proof_summary,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[SubmissionArchiveItemResponse.model_validate(item) for item in items],
    )


def _to_set_response(result: tuple) -> SubmissionArchiveSetResponse:
    archive_set, records = result
    return SubmissionArchiveSetResponse(
        submission_archive_set_id=archive_set.submission_archive_set_id,
        deal_id=archive_set.deal_id,
        archive_status=archive_set.archive_status,
        created_at=archive_set.created_at,
        updated_at=archive_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/submission-archive/build", response_model=SubmissionArchiveSetResponse, status_code=status.HTTP_201_CREATED)
def build_submission_archive_route(
    payload: BuildSubmissionArchiveRequest,
    session: DBSession,
) -> SubmissionArchiveSetResponse:
    archive_set = build_submission_archive(session, payload)
    return _to_set_response(get_submission_archive_set(session, archive_set.submission_archive_set_id))


@router.get("/submission-archive/{submission_archive_set_id}", response_model=SubmissionArchiveSetResponse)
def get_submission_archive_set_route(
    submission_archive_set_id: str,
    session: DBSession,
) -> SubmissionArchiveSetResponse:
    return _to_set_response(get_submission_archive_set(session, submission_archive_set_id))


@router.get("/submission-archive", response_model=list[SubmissionArchiveSetResponse])
def list_submission_archive_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SubmissionArchiveSetResponse]:
    return [_to_set_response(item) for item in list_submission_archive_sets(session, deal_id=deal_id)]


@router.get("/submission-archive/records/{submission_archive_id}", response_model=SubmissionArchiveRecordResponse)
def get_submission_archive_record_route(
    submission_archive_id: str,
    session: DBSession,
) -> SubmissionArchiveRecordResponse:
    return _to_record_response(get_submission_archive_record(session, submission_archive_id))
