from datetime import datetime

from pydantic import Field

from src.shared.enums import HumanReviewStatus
from src.shared.types.common import APIModel


class CreateRuntimeMetadataSliceRequest(APIModel):
    runtime_slice: str = "MVP_RUNTIME_PHASE_1"
    linked_agent_profile_id: str
    linked_prompt_schema_id: str
    allowed_runtime_contexts: list[str] = Field(default_factory=list)
    forbidden_runtime_contexts: list[str] = Field(default_factory=list)
    review_status: HumanReviewStatus = HumanReviewStatus.NEEDS_HUMAN_REVIEW
    trace_refs: list[str] = Field(default_factory=list)
    notes: str | None = None


class UpdateRuntimeMetadataSliceReviewRequest(APIModel):
    review_status: HumanReviewStatus
    notes: str | None = None


class RuntimeMetadataSliceResponse(APIModel):
    runtime_metadata_slice_id: str
    runtime_slice: str
    linked_agent_profile_id: str
    linked_prompt_schema_id: str
    allowed_runtime_contexts: list[str]
    forbidden_runtime_contexts: list[str]
    review_status: HumanReviewStatus
    trace_refs: list[str]
    notes: str | None
    created_at: datetime
    updated_at: datetime
