from datetime import datetime

from pydantic import Field

from src.shared.enums import (
    AgentActivationState,
    AgentLifecycleStatus,
    AgentPromptLinkStatus,
    AgentRegistryStatus,
    HumanReviewStatus,
)
from src.shared.types.common import APIModel


class BuildAgentRegistryEntryInput(APIModel):
    agent_key: str | None = None
    agent_label: str | None = None
    agent_role_name: str | None = None
    owner_role: str | None = None
    owner_operator: str | None = None
    reviewer_role: str | None = None
    activation_state: AgentActivationState | None = None
    lifecycle_status: AgentLifecycleStatus | None = None
    approval_reference: str | None = None
    description: str | None = None
    capability_tags: list[str] = Field(default_factory=list)
    allowed_action_classes: list[str] = Field(default_factory=list)
    forbidden_action_classes: list[str] = Field(default_factory=list)
    allowed_capabilities_json: list[str] = Field(default_factory=list)
    blocked_capabilities_json: list[str] = Field(default_factory=list)
    notes: str | None = None


class BuildAgentRegistryRequest(APIModel):
    registry_scope: str = "INTERNAL"
    entries: list[BuildAgentRegistryEntryInput] = Field(default_factory=list)


class AgentPromptLinkResponse(APIModel):
    prompt_schema_id: str
    link_status: AgentPromptLinkStatus
    created_at: datetime


class AgentRegistryRecordResponse(APIModel):
    agent_registry_id: str
    agent_profile_id: str
    agent_key: str
    agent_label: str
    agent_role_name: str
    description: str | None
    capability_tags: list[str]
    allowed_action_classes: list[str]
    forbidden_action_classes: list[str]
    owner_role: str
    owner_operator: str
    reviewer_role: str
    activation_state: AgentActivationState
    lifecycle_status: AgentLifecycleStatus
    review_status: HumanReviewStatus
    approval_reference: str | None
    allowed_capabilities_json: list[str]
    blocked_capabilities_json: list[str]
    notes: str | None
    created_at: datetime
    updated_at: datetime
    prompt_links: list[AgentPromptLinkResponse]


class AgentRegistrySetResponse(APIModel):
    agent_registry_set_id: str
    registry_scope: str
    registry_status: AgentRegistryStatus
    created_at: datetime
    updated_at: datetime
    records: list[AgentRegistryRecordResponse]
