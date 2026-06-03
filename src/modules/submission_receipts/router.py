from fastapi import APIRouter, Query, status

from src.modules.submission_receipts.schemas import (
    RegisterSubmissionReceiptRequest,
    SubmissionReceiptBindingResponse,
    SubmissionReceiptRecordResponse,
    SubmissionReceiptSetResponse,
)
from src.modules.submission_receipts.service import (
    get_submission_receipt_record,
    get_submission_receipt_set,
    list_submission_receipt_sets,
    register_submission_receipt,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["submission-receipts"])


def _to_binding_response(item) -> SubmissionReceiptBindingResponse:
    return SubmissionReceiptBindingResponse.model_validate(item)


def _to_record_response(result: tuple) -> SubmissionReceiptRecordResponse:
    record, bindings = result
    return SubmissionReceiptRecordResponse(
        submission_receipt_id=record.submission_receipt_id,
        submission_receipt_set_id=record.submission_receipt_set_id,
        receipt_number=record.receipt_number,
        receipt_timestamp=record.receipt_timestamp,
        receipt_source=record.receipt_source,
        created_at=record.created_at,
        updated_at=record.updated_at,
        bindings=[_to_binding_response(item) for item in bindings],
    )


def _to_set_response(result: tuple) -> SubmissionReceiptSetResponse:
    receipt_set, records = result
    return SubmissionReceiptSetResponse(
        submission_receipt_set_id=receipt_set.submission_receipt_set_id,
        deal_id=receipt_set.deal_id,
        submission_execution_set_id=receipt_set.submission_execution_set_id,
        receipt_status=receipt_set.receipt_status,
        created_at=receipt_set.created_at,
        updated_at=receipt_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post(
    "/submission-receipts/register",
    response_model=SubmissionReceiptSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def register_submission_receipt_route(
    payload: RegisterSubmissionReceiptRequest,
    session: DBSession,
) -> SubmissionReceiptSetResponse:
    receipt_set = register_submission_receipt(session, payload)
    return _to_set_response(get_submission_receipt_set(session, receipt_set.submission_receipt_set_id))


@router.get("/submission-receipts/{submission_receipt_set_id}", response_model=SubmissionReceiptSetResponse)
def get_submission_receipt_set_route(
    submission_receipt_set_id: str,
    session: DBSession,
) -> SubmissionReceiptSetResponse:
    return _to_set_response(get_submission_receipt_set(session, submission_receipt_set_id))


@router.get("/submission-receipts", response_model=list[SubmissionReceiptSetResponse])
def list_submission_receipt_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[SubmissionReceiptSetResponse]:
    return [_to_set_response(item) for item in list_submission_receipt_sets(session, deal_id=deal_id)]


@router.get("/submission-receipts/records/{submission_receipt_id}", response_model=SubmissionReceiptRecordResponse)
def get_submission_receipt_record_route(
    submission_receipt_id: str,
    session: DBSession,
) -> SubmissionReceiptRecordResponse:
    return _to_record_response(get_submission_receipt_record(session, submission_receipt_id))
