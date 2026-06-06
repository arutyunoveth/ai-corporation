from datetime import datetime

from pydantic import Field

from src.shared.enums import AgentActivationState, AgentPromptLinkStatus, AgentRegistryStatus
from src.shared.types.common import APIModel


class BuildAgentRegistryEntryInput(APIModel):
    agent_key: str
    agent_label: str
    owner_role: str
    reviewer_role: str
    activation_state: AgentActivationState = AgentActivationState.REVIEWED
    approval_reference: str | None = None
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
    agent_key: str
    agent_label: str
    owner_role: str
    reviewer_role: str
    activation_state: AgentActivationState
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
