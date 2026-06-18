"""Tests for company agent seed data completeness and correctness."""

from src.modules.agent_registry.company_agents import (
    COMPANY_AGENTS,
    INACTIVE_AGENTS,
    build_company_agent_registry_request,
    get_active_company_agents,
    get_inactive_company_agents,
)
from src.shared.enums import (
    AgentKind,
    AgentScope,
    CompanyAgentActivationState,
    DataPolicy,
    ModelTier,
    RuntimeMode,
)

EXPECTED_ACTIVE_KEYS = {"A00", "A10", "A11", "A20", "A21", "A40", "A42"}


def test_active_company_agents_count_is_seven():
    active = get_active_company_agents()
    assert len(active) == 7


def test_all_company_agents_count_is_twenty_one():
    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    assert len(all_agents) == 21


def test_a00_exists():
    keys = {a.agent_key for a in COMPANY_AGENTS + INACTIVE_AGENTS}
    assert "A00" in keys


def test_a10_exists():
    keys = {a.agent_key for a in COMPANY_AGENTS + INACTIVE_AGENTS}
    assert "A10" in keys


def test_a42_exists():
    keys = {a.agent_key for a in COMPANY_AGENTS + INACTIVE_AGENTS}
    assert "A42" in keys


def test_active_agent_keys_are_correct():
    active = get_active_company_agents()
    active_keys = {a.agent_key for a in active}
    assert active_keys == EXPECTED_ACTIVE_KEYS


def test_all_active_company_agents_have_runtime_mode_metadata_only_or_manual_context():
    active = get_active_company_agents()
    for agent in active:
        assert agent.runtime_mode in (RuntimeMode.MANUAL_CONTEXT_ONLY, RuntimeMode.METADATA_ONLY), (
            f"{agent.agent_key} has unexpected runtime_mode: {agent.runtime_mode}"
        )


def test_all_active_company_agents_execution_not_allowed():
    active = get_active_company_agents()
    for agent in active:
        assert agent.runtime_mode in (RuntimeMode.MANUAL_CONTEXT_ONLY, RuntimeMode.METADATA_ONLY)


def test_all_active_company_agents_have_activation_state_active_metadata_only():
    active = get_active_company_agents()
    for agent in active:
        assert agent.activation_state == CompanyAgentActivationState.ACTIVE_METADATA_ONLY


def test_all_company_agents_have_agent_scope():
    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        assert agent.agent_scope == AgentScope.COMPANY_OPERATIONS


def test_all_company_agents_have_agent_kind():
    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        assert isinstance(agent.agent_kind, AgentKind)


def test_all_company_agents_have_data_policy():
    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        assert isinstance(agent.data_policy, DataPolicy)


def test_all_company_agents_have_model_tier():
    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        assert isinstance(agent.model_tier, ModelTier)


def test_build_request_has_all_entries():
    request = build_company_agent_registry_request()
    assert len(request.entries) == 21
    assert request.registry_scope == "COMPANY_OPERATIONS"


def test_inactive_agents_are_draft_or_inactive():
    for agent in INACTIVE_AGENTS:
        assert agent.activation_state in (
            CompanyAgentActivationState.INACTIVE,
            CompanyAgentActivationState.DRAFT,
        ), f"{agent.agent_key} has unexpected activation_state: {agent.activation_state}"


def test_no_duplicate_agent_keys():
    all_keys = [a.agent_key for a in COMPANY_AGENTS + INACTIVE_AGENTS]
    assert len(all_keys) == len(set(all_keys)), "Duplicate agent keys found"
