from fastapi import APIRouter, Query, status

from src.modules.agent_registry.schemas import (
    AgentPromptLinkResponse,
    AgentRegistryRecordResponse,
    AgentRegistrySetResponse,
    BuildAgentRegistryRequest,
)
from src.modules.agent_registry.service import (
    build_agent_registry,
    get_agent_registry_record,
    get_agent_registry_set,
    list_agent_registry_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import HumanReviewStatus

router = APIRouter(tags=["agent-registry"])


def _to_link_response(item) -> AgentPromptLinkResponse:
    return AgentPromptLinkResponse.model_validate(item)


def _to_record_response(result: tuple) -> AgentRegistryRecordResponse:
    record, links = result
    return AgentRegistryRecordResponse(
        agent_registry_id=record.agent_registry_id,
        agent_profile_id=record.agent_registry_id,
        agent_key=record.agent_key,
        agent_label=record.agent_label,
        agent_role_name=record.agent_label,
        description=record.description or record.notes,
        capability_tags=record.allowed_capabilities_json,
        allowed_action_classes=record.allowed_capabilities_json,
        forbidden_action_classes=record.blocked_capabilities_json,
        owner_role=record.owner_role,
        owner_operator=record.owner_role,
        reviewer_role=record.reviewer_role,
        activation_state=record.activation_state,
        lifecycle_status=record.activation_state,
        review_status=HumanReviewStatus.APPROVED_FOR_INTERNAL_USE,
        approval_reference=record.approval_reference,
        allowed_capabilities_json=record.allowed_capabilities_json,
        blocked_capabilities_json=record.blocked_capabilities_json,
        notes=record.notes,
        agent_scope=record.agent_scope,
        agent_kind=record.agent_kind,
        reports_to=record.reports_to,
        data_policy=record.data_policy,
        runtime_mode=record.runtime_mode,
        model_tier=record.model_tier,
        responsibilities=record.responsibilities_json,
        inputs=record.inputs_json,
        outputs=record.outputs_json,
        escalation_rules=record.escalation_rules_json,
        forbidden_actions=record.forbidden_actions_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        prompt_links=[_to_link_response(item) for item in links],
    )


def _to_set_response(result: tuple) -> AgentRegistrySetResponse:
    registry_set, records = result
    return AgentRegistrySetResponse(
        agent_registry_set_id=registry_set.agent_registry_set_id,
        registry_scope=registry_set.registry_scope,
        registry_status=registry_set.registry_status,
        created_at=registry_set.created_at,
        updated_at=registry_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/agent-registry/build", response_model=AgentRegistrySetResponse, status_code=status.HTTP_201_CREATED)
def build_agent_registry_route(payload: BuildAgentRegistryRequest, session: DBSession) -> AgentRegistrySetResponse:
    registry_set = build_agent_registry(session, payload)
    return _to_set_response(get_agent_registry_set(session, registry_set.agent_registry_set_id))


@router.get("/agent-registry/{agent_registry_set_id}", response_model=AgentRegistrySetResponse)
def get_agent_registry_set_route(agent_registry_set_id: str, session: DBSession) -> AgentRegistrySetResponse:
    return _to_set_response(get_agent_registry_set(session, agent_registry_set_id))


@router.get("/agent-registry", response_model=list[AgentRegistrySetResponse])
def list_agent_registry_sets_route(
    session: DBSession,
    registry_scope: str | None = Query(default=None),
) -> list[AgentRegistrySetResponse]:
    return [_to_set_response(item) for item in list_agent_registry_sets(session, registry_scope=registry_scope)]


@router.get("/agent-registry/records/{agent_registry_id}", response_model=AgentRegistryRecordResponse)
def get_agent_registry_record_route(agent_registry_id: str, session: DBSession) -> AgentRegistryRecordResponse:
    return _to_record_response(get_agent_registry_record(session, agent_registry_id))
