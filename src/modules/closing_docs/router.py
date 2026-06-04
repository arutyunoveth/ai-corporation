from fastapi import APIRouter, Query, status

from src.modules.closing_docs.schemas import (
    BuildClosingDocsRequest,
    ClosingDocsFlagResponse,
    ClosingDocsItemResponse,
    ClosingDocsRecordResponse,
    ClosingDocsSetResponse,
)
from src.modules.closing_docs.service import (
    build_closing_docs,
    get_closing_docs_record,
    get_closing_docs_set,
    list_closing_docs_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["closing-docs"])


def _to_record_response(result: tuple) -> ClosingDocsRecordResponse:
    record, items, flags = result
    return ClosingDocsRecordResponse(
        closing_docs_id=record.closing_docs_id,
        docs_manifest_json=record.docs_manifest_json,
        summary_text=record.summary_text,
        created_at=record.created_at,
        updated_at=record.updated_at,
        items=[ClosingDocsItemResponse.model_validate(item) for item in items],
        flags=[ClosingDocsFlagResponse.model_validate(item) for item in flags],
    )


def _to_set_response(result: tuple) -> ClosingDocsSetResponse:
    docs_set, records = result
    return ClosingDocsSetResponse(
        closing_docs_set_id=docs_set.closing_docs_set_id,
        deal_id=docs_set.deal_id,
        docs_status=docs_set.docs_status,
        created_at=docs_set.created_at,
        updated_at=docs_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/closing-docs/build", response_model=ClosingDocsSetResponse, status_code=status.HTTP_201_CREATED)
def build_closing_docs_route(payload: BuildClosingDocsRequest, session: DBSession) -> ClosingDocsSetResponse:
    docs_set = build_closing_docs(session, payload)
    return _to_set_response(get_closing_docs_set(session, docs_set.closing_docs_set_id))


@router.get("/closing-docs/{closing_docs_set_id}", response_model=ClosingDocsSetResponse)
def get_closing_docs_set_route(closing_docs_set_id: str, session: DBSession) -> ClosingDocsSetResponse:
    return _to_set_response(get_closing_docs_set(session, closing_docs_set_id))


@router.get("/closing-docs", response_model=list[ClosingDocsSetResponse])
def list_closing_docs_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ClosingDocsSetResponse]:
    return [_to_set_response(item) for item in list_closing_docs_sets(session, deal_id=deal_id)]


@router.get("/closing-docs/records/{closing_docs_id}", response_model=ClosingDocsRecordResponse)
def get_closing_docs_record_route(closing_docs_id: str, session: DBSession) -> ClosingDocsRecordResponse:
    return _to_record_response(get_closing_docs_record(session, closing_docs_id))
