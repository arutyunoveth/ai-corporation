from fastapi import APIRouter, Query, status

from src.modules.runtime_metadata_slices.schemas import (
    CreateRuntimeMetadataSliceRequest,
    RuntimeMetadataSliceResponse,
    UpdateRuntimeMetadataSliceReviewRequest,
)
from src.modules.runtime_metadata_slices.service import (
    create_runtime_metadata_slice,
    get_runtime_metadata_slice,
    list_runtime_metadata_slices,
    update_runtime_metadata_slice_review,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["runtime-metadata-slices"])


def _to_response(runtime_slice) -> RuntimeMetadataSliceResponse:
    return RuntimeMetadataSliceResponse(
        runtime_metadata_slice_id=runtime_slice.runtime_metadata_slice_id,
        runtime_slice=runtime_slice.runtime_slice,
        linked_agent_profile_id=runtime_slice.linked_agent_profile_id,
        linked_prompt_schema_id=runtime_slice.linked_prompt_schema_id,
        allowed_runtime_contexts=runtime_slice.allowed_runtime_contexts,
        forbidden_runtime_contexts=runtime_slice.forbidden_runtime_contexts,
        review_status=runtime_slice.review_status,
        trace_refs=runtime_slice.trace_refs_json,
        notes=runtime_slice.notes,
        created_at=runtime_slice.created_at,
        updated_at=runtime_slice.updated_at,
    )


@router.post(
    "/runtime-metadata-slices",
    response_model=RuntimeMetadataSliceResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_runtime_metadata_slice_route(
    payload: CreateRuntimeMetadataSliceRequest,
    session: DBSession,
) -> RuntimeMetadataSliceResponse:
    return _to_response(create_runtime_metadata_slice(session, payload))


@router.get("/runtime-metadata-slices/{runtime_metadata_slice_id}", response_model=RuntimeMetadataSliceResponse)
def get_runtime_metadata_slice_route(
    runtime_metadata_slice_id: str,
    session: DBSession,
) -> RuntimeMetadataSliceResponse:
    return _to_response(get_runtime_metadata_slice(session, runtime_metadata_slice_id))


@router.get("/runtime-metadata-slices", response_model=list[RuntimeMetadataSliceResponse])
def list_runtime_metadata_slices_route(
    session: DBSession,
    runtime_slice: str | None = Query(default=None),
) -> list[RuntimeMetadataSliceResponse]:
    return [_to_response(item) for item in list_runtime_metadata_slices(session, runtime_slice=runtime_slice)]


@router.patch(
    "/runtime-metadata-slices/{runtime_metadata_slice_id}/review-status",
    response_model=RuntimeMetadataSliceResponse,
)
def update_runtime_metadata_slice_review_route(
    runtime_metadata_slice_id: str,
    payload: UpdateRuntimeMetadataSliceReviewRequest,
    session: DBSession,
) -> RuntimeMetadataSliceResponse:
    return _to_response(update_runtime_metadata_slice_review(session, runtime_metadata_slice_id, payload))
