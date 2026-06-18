"""Internal read-only API endpoints for company agent context.

These endpoints provide read-only access to company agent metadata and context.
No runtime execution, no LLM calls, no autonomous orchestration.
"""

from fastapi import APIRouter, HTTPException

from src.modules.agent_registry.company_agents import (
    COMPANY_AGENTS,
    INACTIVE_AGENTS,
    get_active_company_agents,
)
from src.modules.agent_registry.schemas import BuildAgentRegistryEntryInput
from src.modules.workflow_runs.company_workflow_routes import (
    get_company_workflow_route,
    list_company_workflow_routes,
)
from scripts.export_company_agent_context import (
    export_agent_context_json,
    export_agent_context_markdown,
    KNOWN_AGENTS,
)
from scripts.export_hermes_company_manifest import build_manifest

router = APIRouter(tags=["internal-company-agents"])


def _agent_to_response(agent: BuildAgentRegistryEntryInput) -> dict:
    return {
        "agent_id": agent.agent_key,
        "display_name": agent.agent_label,
        "agent_scope": agent.agent_scope.value if agent.agent_scope else None,
        "agent_kind": agent.agent_kind.value if agent.agent_kind else None,
        "activation_state": agent.activation_state.value,
        "data_policy": agent.data_policy.value if agent.data_policy else None,
        "runtime_mode": agent.runtime_mode.value if agent.runtime_mode else None,
        "model_tier": agent.model_tier.value if agent.model_tier else None,
        "execution_allowed": False,
    }


@router.get("/internal/company-agents")
def list_company_agents() -> dict:
    active = get_active_company_agents()
    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    return {
        "active_agents": [_agent_to_response(a) for a in active],
        "all_agents": [_agent_to_response(a) for a in all_agents],
        "active_count": len(active),
        "total_count": len(all_agents),
    }


@router.get("/internal/company-agents/{agent_id}")
def get_company_agent(agent_id: str) -> dict:
    all_agents_dict = {a.agent_key: a for a in COMPANY_AGENTS + INACTIVE_AGENTS}
    if agent_id not in all_agents_dict:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    agent = all_agents_dict[agent_id]
    return _agent_to_response(agent)


@router.get("/internal/company-agents/{agent_id}/context")
def get_company_agent_context(agent_id: str, format: str = "json") -> dict:
    if agent_id not in KNOWN_AGENTS:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found or has no context files")

    if format == "markdown":
        content = export_agent_context_markdown(agent_id, include_metadata=True)
        return {"agent_id": agent_id, "format": "markdown", "content": content}
    else:
        content = export_agent_context_json(agent_id, include_metadata=True)
        return {"agent_id": agent_id, "format": "json", "content": content}


@router.get("/internal/company-agents/hermes-manifest")
def get_hermes_manifest() -> dict:
    return build_manifest()
