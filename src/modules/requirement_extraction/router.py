from fastapi import APIRouter, Query, status

from src.modules.requirement_extraction.schemas import (
    BuildRequirementExtractionRequest,
    RequirementExtractionRecordResponse,
    RequirementExtractionSetResponse,
    RequirementSourceLinkResponse,
)
from src.modules.requirement_extraction.service import (
    build_requirement_extraction,
    get_requirement_extraction_record,
    get_requirement_extraction_set,
    list_requirement_extraction_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["requirements"])


def _to_source_link_response(item) -> RequirementSourceLinkResponse:
    return RequirementSourceLinkResponse.model_validate(item)


def _to_record_response(result: tuple) -> RequirementExtractionRecordResponse:
    record, links = result
    return RequirementExtractionRecordResponse(
        requirement_extraction_id=record.requirement_extraction_id,
        requirement_extraction_set_id=record.requirement_extraction_set_id,
        requirement_code=record.requirement_code,
        requirement_text=record.requirement_text,
        requirement_group=record.requirement_group,
        created_at=record.created_at,
        updated_at=record.updated_at,
        source_links=[_to_source_link_response(item) for item in links],
    )


def _to_set_response(result: tuple) -> RequirementExtractionSetResponse:
    extraction_set, records = result
    return RequirementExtractionSetResponse(
        requirement_extraction_set_id=extraction_set.requirement_extraction_set_id,
        document_set_id=extraction_set.document_set_id,
        extraction_status=extraction_set.extraction_status,
        created_at=extraction_set.created_at,
        updated_at=extraction_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/requirements/extract", response_model=RequirementExtractionSetResponse, status_code=status.HTTP_201_CREATED)
def build_requirement_extraction_route(
    payload: BuildRequirementExtractionRequest,
    session: DBSession,
) -> RequirementExtractionSetResponse:
    extraction_set = build_requirement_extraction(session, payload.document_set_id)
    return _to_set_response(get_requirement_extraction_set(session, extraction_set.requirement_extraction_set_id))


@router.get("/requirements/{requirement_extraction_set_id}", response_model=RequirementExtractionSetResponse)
def get_requirement_extraction_set_route(
    requirement_extraction_set_id: str,
    session: DBSession,
) -> RequirementExtractionSetResponse:
    return _to_set_response(get_requirement_extraction_set(session, requirement_extraction_set_id))


@router.get("/requirements", response_model=list[RequirementExtractionSetResponse])
def list_requirement_extraction_sets_route(
    session: DBSession,
    document_set_id: str | None = Query(default=None),
) -> list[RequirementExtractionSetResponse]:
    return [_to_set_response(item) for item in list_requirement_extraction_sets(session, document_set_id=document_set_id)]


@router.get("/requirements/records/{requirement_extraction_id}", response_model=RequirementExtractionRecordResponse)
def get_requirement_extraction_record_route(
    requirement_extraction_id: str,
    session: DBSession,
) -> RequirementExtractionRecordResponse:
    return _to_record_response(get_requirement_extraction_record(session, requirement_extraction_id))
