from src.modules.agent_registry.company_agents import (
    COMPANY_AGENTS,
    INACTIVE_AGENTS,
    build_company_agent_registry_request,
    get_active_company_agents,
    get_inactive_company_agents,
)
from src.modules.agent_registry.models import AgentRegistryRecord, AgentRegistrySet
from src.shared.enums import (
    AgentScope,
    CompanyAgentActivationState,
    DataPolicy,
    RuntimeMode,
)


def test_company_agents_register_through_m049(client, session):
    request = build_company_agent_registry_request()
    response = client.post("/agent-registry/build", json=request.model_dump())
    assert response.status_code == 201
    payload = response.json()
    assert payload["registry_scope"] == "COMPANY_OPERATIONS"
    registry_records = session.query(AgentRegistryRecord).filter_by(
        agent_registry_set_id=payload["agent_registry_set_id"]
    ).all()
    assert len(registry_records) == len(COMPANY_AGENTS) + len(INACTIVE_AGENTS)


def test_company_agents_have_company_operations_scope(client, session):
    request = build_company_agent_registry_request()
    response = client.post("/agent-registry/build", json=request.model_dump())
    assert response.status_code == 201
    payload = response.json()
    for record in payload["records"]:
        assert record["agent_scope"] == AgentScope.COMPANY_OPERATIONS


def test_product_agents_and_company_agents_not_mixed(client, session):
    request = build_company_agent_registry_request()
    response = client.post("/agent-registry/build", json=request.model_dump())
    assert response.status_code == 201
    payload = response.json()
    for record in payload["records"]:
        assert record["agent_scope"] is not None
        assert record["agent_scope"] == AgentScope.COMPANY_OPERATIONS


def test_active_company_agents_count_is_seven():
    active = get_active_company_agents()
    assert len(active) == 7


def test_all_active_company_agents_have_data_policy():
    active = get_active_company_agents()
    for agent in active:
        assert agent.data_policy is not None, f"{agent.agent_key} missing data_policy"
        assert isinstance(agent.data_policy, DataPolicy)


def test_all_active_company_agents_have_runtime_mode():
    active = get_active_company_agents()
    for agent in active:
        assert agent.runtime_mode is not None, f"{agent.agent_key} missing runtime_mode"
        assert agent.runtime_mode in (RuntimeMode.MANUAL_CONTEXT_ONLY, RuntimeMode.METADATA_ONLY)


def test_all_active_company_agents_execution_not_allowed():
    active = get_active_company_agents()
    for agent in active:
        assert agent.runtime_mode in (RuntimeMode.MANUAL_CONTEXT_ONLY, RuntimeMode.METADATA_ONLY), (
            f"{agent.agent_key} has unexpected runtime_mode: {agent.runtime_mode}"
        )


def test_all_active_company_agents_have_activation_state():
    active = get_active_company_agents()
    for agent in active:
        assert agent.activation_state == CompanyAgentActivationState.ACTIVE_METADATA_ONLY, (
            f"{agent.agent_key} has unexpected activation_state: {agent.activation_state}"
        )
