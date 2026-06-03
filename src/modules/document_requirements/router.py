from fastapi import APIRouter, Query, status

from src.modules.document_requirements.schemas import (
    DocumentRequirementRowResponse,
    DocumentRequirementSetResponse,
    ExtractDocumentRequirementsRequest,
)
from src.modules.document_requirements.service import (
    extract_document_requirements,
    get_document_requirement_set,
    list_document_requirement_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["document-requirements"])


def _to_response(result: tuple) -> DocumentRequirementSetResponse:
    requirement_set, rows = result
    return DocumentRequirementSetResponse(
        document_requirement_set_id=requirement_set.document_requirement_set_id,
        deal_id=requirement_set.deal_id,
        intake_id=requirement_set.intake_id,
        document_set_id=requirement_set.document_set_id,
        tender_summary_id=requirement_set.tender_summary_id,
        requirement_count=requirement_set.requirement_count,
        requires_manual_review=requirement_set.requires_manual_review,
        notes=requirement_set.notes,
        created_at=requirement_set.created_at,
        updated_at=requirement_set.updated_at,
        rows=[DocumentRequirementRowResponse.model_validate(row) for row in rows],
    )


@router.post(
    "/document-requirements/extract",
    response_model=DocumentRequirementSetResponse,
    status_code=status.HTTP_201_CREATED,
)
def extract_document_requirements_route(
    payload: ExtractDocumentRequirementsRequest,
    session: DBSession,
) -> DocumentRequirementSetResponse:
    return _to_response(extract_document_requirements(session, payload))


@router.get("/document-requirements/{document_requirement_set_id}", response_model=DocumentRequirementSetResponse)
def get_document_requirement_set_route(
    document_requirement_set_id: str,
    session: DBSession,
) -> DocumentRequirementSetResponse:
    return _to_response(get_document_requirement_set(session, document_requirement_set_id))


@router.get("/document-requirements", response_model=list[DocumentRequirementSetResponse])
def list_document_requirement_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[DocumentRequirementSetResponse]:
    return [_to_response(item) for item in list_document_requirement_sets(session, deal_id=deal_id)]

