from fastapi import APIRouter, Query, status

from src.modules.prompt_schema_library.schemas import (
    BuildPromptSchemaLibraryRequest,
    PromptSchemaLibrarySetResponse,
    PromptSchemaLinkResponse,
    PromptSchemaRecordResponse,
)
from src.modules.prompt_schema_library.service import (
    build_prompt_schema_library,
    get_prompt_schema_library_set,
    get_prompt_schema_record,
    list_prompt_schema_library_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import HumanReviewStatus, PromptRiskClass, PromptValidationMode

router = APIRouter(tags=["prompt-schema-library"])


def _to_link_response(item) -> PromptSchemaLinkResponse:
    return PromptSchemaLinkResponse(
        agent_registry_id=item.agent_registry_id,
        link_status=item.link_status,
        created_at=item.created_at,
    )


def _to_record_response(result: tuple) -> PromptSchemaRecordResponse:
    record, links = result
    runtime_metadata = record.asset_payload_json.get("runtime_metadata", {}) if record.asset_payload_json else {}
    return PromptSchemaRecordResponse(
        prompt_schema_id=record.prompt_schema_id,
        asset_key=record.asset_key,
        prompt_name=runtime_metadata.get("prompt_name", record.asset_key),
        asset_type=record.asset_type,
        version_tag=record.version_tag,
        prompt_version=runtime_metadata.get("prompt_version", record.version_tag),
        owner_role=record.owner_role,
        owner_operator=runtime_metadata.get("owner_operator", record.owner_role),
        reviewer_role=record.reviewer_role,
        asset_status=record.asset_status,
        review_status=HumanReviewStatus(
            runtime_metadata.get("review_status", HumanReviewStatus.APPROVED_FOR_INTERNAL_USE)
        ),
        prompt_purpose=runtime_metadata.get("prompt_purpose", record.usage_constraints_text),
        intended_use_case=runtime_metadata.get("intended_use_case", "bounded_internal_metadata_control"),
        associated_runtime_slice=runtime_metadata.get("associated_runtime_slice", "MVP_RUNTIME_PHASE_1"),
        usage_constraints_text=record.usage_constraints_text,
        input_schema_ref=record.input_schema_ref,
        output_schema_ref=record.output_schema_ref,
        validation_mode=PromptValidationMode(runtime_metadata.get("validation_mode", PromptValidationMode.SCHEMA_REQUIRED)),
        compatible_output_schema=runtime_metadata.get("compatible_output_schema", record.output_schema_ref),
        allowed_use_contexts=runtime_metadata.get("allowed_use_contexts", []),
        forbidden_use_contexts=runtime_metadata.get("forbidden_use_contexts", []),
        human_review_required=runtime_metadata.get("human_review_required", True),
        risk_class=PromptRiskClass(runtime_metadata.get("risk_class", PromptRiskClass.MEDIUM)),
        notes=runtime_metadata.get("notes", record.safety_notes),
        safety_notes=record.safety_notes,
        rationale=runtime_metadata.get("rationale", record.safety_notes),
        asset_payload_json=record.asset_payload_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        agent_links=[_to_link_response(item) for item in links],
    )


def _to_set_response(result: tuple) -> PromptSchemaLibrarySetResponse:
    library_set, records = result
    return PromptSchemaLibrarySetResponse(
        prompt_schema_library_set_id=library_set.prompt_schema_library_set_id,
        library_scope=library_set.library_scope,
        library_status=library_set.library_status,
        created_at=library_set.created_at,
        updated_at=library_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post(
    "/prompt-schema-library/build",
    response_model=PromptSchemaLibrarySetResponse,
    status_code=status.HTTP_201_CREATED,
)
def build_prompt_schema_library_route(
    payload: BuildPromptSchemaLibraryRequest,
    session: DBSession,
) -> PromptSchemaLibrarySetResponse:
    library_set = build_prompt_schema_library(session, payload)
    return _to_set_response(get_prompt_schema_library_set(session, library_set.prompt_schema_library_set_id))


@router.get("/prompt-schema-library/{prompt_schema_library_set_id}", response_model=PromptSchemaLibrarySetResponse)
def get_prompt_schema_library_set_route(
    prompt_schema_library_set_id: str,
    session: DBSession,
) -> PromptSchemaLibrarySetResponse:
    return _to_set_response(get_prompt_schema_library_set(session, prompt_schema_library_set_id))


@router.get("/prompt-schema-library", response_model=list[PromptSchemaLibrarySetResponse])
def list_prompt_schema_library_sets_route(
    session: DBSession,
    library_scope: str | None = Query(default=None),
) -> list[PromptSchemaLibrarySetResponse]:
    return [_to_set_response(item) for item in list_prompt_schema_library_sets(session, library_scope=library_scope)]


@router.get("/prompt-schema-library/records/{prompt_schema_id}", response_model=PromptSchemaRecordResponse)
def get_prompt_schema_record_route(prompt_schema_id: str, session: DBSession) -> PromptSchemaRecordResponse:
    return _to_record_response(get_prompt_schema_record(session, prompt_schema_id))
