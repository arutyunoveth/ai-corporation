from datetime import datetime

from pydantic import Field

from src.shared.enums import (
    AgentPromptLinkStatus,
    HumanReviewStatus,
    PromptRiskClass,
    PromptSchemaAssetStatus,
    PromptSchemaAssetType,
    PromptSchemaLibraryStatus,
    PromptValidationMode,
)
from src.shared.types.common import APIModel


class BuildPromptSchemaAssetInput(APIModel):
    asset_key: str | None = None
    prompt_name: str | None = None
    asset_type: PromptSchemaAssetType = PromptSchemaAssetType.PROMPT_TEMPLATE
    version_tag: str | None = None
    prompt_version: str | None = None
    owner_role: str | None = None
    owner_operator: str | None = None
    reviewer_role: str | None = None
    asset_status: PromptSchemaAssetStatus = PromptSchemaAssetStatus.REVIEWED
    review_status: HumanReviewStatus = HumanReviewStatus.APPROVED_FOR_INTERNAL_USE
    prompt_purpose: str | None = None
    intended_use_case: str | None = None
    associated_runtime_slice: str | None = None
    usage_constraints_text: str | None = None
    input_schema_ref: str | None = None
    output_schema_ref: str | None = None
    validation_mode: PromptValidationMode = PromptValidationMode.NONE
    compatible_output_schema: str | None = None
    allowed_use_contexts: list[str] = Field(default_factory=list)
    forbidden_use_contexts: list[str] = Field(default_factory=list)
    human_review_required: bool = True
    risk_class: PromptRiskClass = PromptRiskClass.MEDIUM
    notes: str | None = None
    safety_notes: str | None = None
    rationale: str | None = None
    asset_payload_json: dict = Field(default_factory=dict)
    linked_agent_registry_ids: list[str] = Field(default_factory=list)


class BuildPromptSchemaLibraryRequest(APIModel):
    library_scope: str = "INTERNAL"
    assets: list[BuildPromptSchemaAssetInput] = Field(default_factory=list)


class PromptSchemaLinkResponse(APIModel):
    agent_registry_id: str
    link_status: AgentPromptLinkStatus
    created_at: datetime


class PromptSchemaRecordResponse(APIModel):
    prompt_schema_id: str
    asset_key: str
    prompt_name: str
    asset_type: PromptSchemaAssetType
    version_tag: str
    prompt_version: str
    owner_role: str
    owner_operator: str
    reviewer_role: str
    asset_status: PromptSchemaAssetStatus
    review_status: HumanReviewStatus
    prompt_purpose: str
    intended_use_case: str
    associated_runtime_slice: str
    usage_constraints_text: str
    input_schema_ref: str | None
    output_schema_ref: str | None
    validation_mode: PromptValidationMode
    compatible_output_schema: str | None
    allowed_use_contexts: list[str]
    forbidden_use_contexts: list[str]
    human_review_required: bool
    risk_class: PromptRiskClass
    notes: str | None
    safety_notes: str | None
    rationale: str | None
    asset_payload_json: dict
    created_at: datetime
    updated_at: datetime
    agent_links: list[PromptSchemaLinkResponse]


class PromptSchemaLibrarySetResponse(APIModel):
    prompt_schema_library_set_id: str
    library_scope: str
    library_status: PromptSchemaLibraryStatus
    created_at: datetime
    updated_at: datetime
    records: list[PromptSchemaRecordResponse]
