from datetime import datetime

from src.shared.enums import (
    HumanReviewStatus,
    RuntimeTraceActionType,
    RuntimeTraceActorType,
    RuntimeTraceDisposition,
    RuntimeTraceValidationStatus,
)
from src.shared.types.common import APIModel


class CreateRuntimeControlTraceRequest(APIModel):
    runtime_slice: str = "MVP_RUNTIME_PHASE_1"
    source_entity: str
    actor_type: RuntimeTraceActorType
    actor_ref: str
    action_type: RuntimeTraceActionType
    target_module: str | None = None
    target_record_id: str | None = None
    prompt_schema_ref: str | None = None
    agent_profile_ref: str | None = None
    input_artifact_ref: str | None = None
    output_artifact_ref: str | None = None
    input_summary: str | None = None
    output_summary: str | None = None
    validation_status: RuntimeTraceValidationStatus = RuntimeTraceValidationStatus.PENDING
    human_review_status: HumanReviewStatus = HumanReviewStatus.NEEDS_HUMAN_REVIEW
    reviewer_operator: str | None = None
    final_disposition: RuntimeTraceDisposition | None = None


class UpdateRuntimeControlTraceReviewRequest(APIModel):
    human_review_status: HumanReviewStatus
    reviewer_operator: str
    final_disposition: RuntimeTraceDisposition | None = None


class RuntimeControlTraceResponse(APIModel):
    runtime_trace_id: str
    runtime_slice: str
    source_entity: str
    actor_type: RuntimeTraceActorType
    actor_ref: str
    action_type: RuntimeTraceActionType
    target_module: str | None
    target_record_id: str | None
    prompt_schema_ref: str | None
    agent_profile_ref: str | None
    input_artifact_ref: str | None
    output_artifact_ref: str | None
    input_summary: str | None
    output_summary: str | None
    validation_status: RuntimeTraceValidationStatus
    human_review_status: HumanReviewStatus
    reviewer_operator: str | None
    final_disposition: RuntimeTraceDisposition | None
    created_at: datetime
    updated_at: datetime
