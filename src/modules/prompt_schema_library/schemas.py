from datetime import datetime

from pydantic import Field

from src.shared.enums import AgentPromptLinkStatus, PromptSchemaAssetStatus, PromptSchemaAssetType, PromptSchemaLibraryStatus
from src.shared.types.common import APIModel


class BuildPromptSchemaAssetInput(APIModel):
    asset_key: str
    asset_type: PromptSchemaAssetType
    version_tag: str
    owner_role: str
    reviewer_role: str
    asset_status: PromptSchemaAssetStatus = PromptSchemaAssetStatus.REVIEWED
    usage_constraints_text: str
    input_schema_ref: str | None = None
    output_schema_ref: str | None = None
    safety_notes: str | None = None
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
    asset_type: PromptSchemaAssetType
    version_tag: str
    owner_role: str
    reviewer_role: str
    asset_status: PromptSchemaAssetStatus
    usage_constraints_text: str
    input_schema_ref: str | None
    output_schema_ref: str | None
    safety_notes: str | None
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
