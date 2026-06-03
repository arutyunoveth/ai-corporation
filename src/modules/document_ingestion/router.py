from fastapi import APIRouter, Query, status

from src.modules.document_ingestion.schemas import (
    CreateDocumentIngestionRunRequest,
    CreateDocumentSetRequest,
    CreateDocumentSetResponse,
    DocumentIngestionRunResponse,
    DocumentSetItemResponse,
    DocumentSetResponse,
)
from src.modules.document_ingestion.service import create_document_ingestion_run, create_document_set, get_document_set, list_document_sets
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["document-ingestion"])


def _to_document_set_response(result: tuple) -> DocumentSetResponse:
    document_set, items, runs = result
    return DocumentSetResponse(
        document_set_id=document_set.document_set_id,
        deal_id=document_set.deal_id,
        intake_id=document_set.intake_id,
        set_type=document_set.set_type,
        ingestion_status=document_set.ingestion_status,
        item_count=document_set.item_count,
        created_at=document_set.created_at,
        updated_at=document_set.updated_at,
        items=[DocumentSetItemResponse.model_validate(item) for item in items],
        runs=[DocumentIngestionRunResponse.model_validate(run) for run in runs],
    )


@router.post("/document-ingestion/sets", response_model=CreateDocumentSetResponse, status_code=status.HTTP_201_CREATED)
def create_document_set_route(payload: CreateDocumentSetRequest, session: DBSession) -> CreateDocumentSetResponse:
    document_set = create_document_set(session, payload)
    return CreateDocumentSetResponse(
        document_set_id=document_set.document_set_id,
        ingestion_status=document_set.ingestion_status,
        item_count=document_set.item_count,
    )


@router.get("/document-ingestion/sets/{document_set_id}", response_model=DocumentSetResponse)
def get_document_set_route(document_set_id: str, session: DBSession) -> DocumentSetResponse:
    return _to_document_set_response(get_document_set(session, document_set_id))


@router.get("/document-ingestion/sets", response_model=list[DocumentSetResponse])
def list_document_sets_route(session: DBSession, deal_id: str | None = Query(default=None)) -> list[DocumentSetResponse]:
    return [_to_document_set_response(item) for item in list_document_sets(session, deal_id=deal_id)]


@router.post(
    "/document-ingestion/sets/{document_set_id}/runs",
    response_model=DocumentIngestionRunResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_document_ingestion_run_route(
    document_set_id: str,
    payload: CreateDocumentIngestionRunRequest,
    session: DBSession,
) -> DocumentIngestionRunResponse:
    return DocumentIngestionRunResponse.model_validate(create_document_ingestion_run(session, document_set_id, payload))

