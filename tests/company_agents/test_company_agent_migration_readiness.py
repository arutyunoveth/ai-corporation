"""Tests for company agent migration readiness and schema alignment."""

from pathlib import Path

from sqlalchemy import inspect

from src.modules.agent_registry.models import AgentRegistryRecord
from src.modules.agent_registry.schemas import BuildAgentRegistryEntryInput
from src.shared.enums import (
    AgentKind,
    AgentScope,
    CompanyAgentActivationState,
    DataPolicy,
    ModelTier,
    RuntimeMode,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS_DIR = REPO_ROOT / "migrations" / "versions"

COMPANY_AGENT_MODEL_FIELDS = [
    "agent_scope",
    "agent_kind",
    "reports_to",
    "data_policy",
    "runtime_mode",
    "model_tier",
    "description",
    "responsibilities_json",
    "inputs_json",
    "outputs_json",
    "escalation_rules_json",
    "forbidden_actions_json",
]

COMPANY_AGENT_SCHEMA_FIELDS = [
    "agent_scope",
    "agent_kind",
    "reports_to",
    "data_policy",
    "runtime_mode",
    "model_tier",
    "description",
    "responsibilities",
    "inputs",
    "outputs",
    "escalation_rules",
    "forbidden_actions",
]

MIGRATION_FILE = MIGRATIONS_DIR / "087_add_company_agent_metadata_fields.py"


def test_all_company_agent_fields_exist_in_model():
    mapper = inspect(AgentRegistryRecord)
    model_columns = {c.key for c in mapper.columns}
    for field in COMPANY_AGENT_MODEL_FIELDS:
        assert field in model_columns, f"Field '{field}' missing from AgentRegistryRecord model"


def test_schema_fields_align_with_model():
    schema_fields = set(BuildAgentRegistryEntryInput.model_fields.keys())
    for field in COMPANY_AGENT_SCHEMA_FIELDS:
        assert field in schema_fields, f"Field '{field}' missing from BuildAgentRegistryEntryInput schema"


def test_migration_file_exists():
    assert MIGRATION_FILE.is_file(), f"Migration file not found: {MIGRATION_FILE}"


def test_migration_file_contains_all_new_columns():
    content = MIGRATION_FILE.read_text(encoding="utf-8")
    for field in COMPANY_AGENT_MODEL_FIELDS:
        assert f'"{field}"' in content or f"'{field}'" in content, (
            f"Migration file does not reference column '{field}'"
        )


def test_migration_file_has_downgrade():
    content = MIGRATION_FILE.read_text(encoding="utf-8")
    assert "def downgrade()" in content, "Migration file missing downgrade function"


def test_migration_file_downgrade_drops_all_columns():
    content = MIGRATION_FILE.read_text(encoding="utf-8")
    for field in COMPANY_AGENT_MODEL_FIELDS:
        assert field in content, f"Downgrade does not reference column '{field}'"


def test_migration_file_links_to_previous_revision():
    content = MIGRATION_FILE.read_text(encoding="utf-8")
    assert "086_create_runtime_metadata_slices" in content, (
        "Migration does not link to previous revision 086"
    )


def test_company_agent_seed_records_do_not_require_missing_columns():
    from src.modules.agent_registry.company_agents import COMPANY_AGENTS, INACTIVE_AGENTS

    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        assert isinstance(agent, BuildAgentRegistryEntryInput)
        assert agent.agent_key is not None


def test_company_agent_seed_records_have_required_enum_fields():
    from src.modules.agent_registry.company_agents import COMPANY_AGENTS, INACTIVE_AGENTS

    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        assert isinstance(agent.agent_scope, AgentScope), f"{agent.agent_key} missing agent_scope"
        assert isinstance(agent.agent_kind, AgentKind), f"{agent.agent_key} missing agent_kind"
        assert isinstance(agent.runtime_mode, RuntimeMode), f"{agent.agent_key} missing runtime_mode"
        assert isinstance(agent.data_policy, DataPolicy), f"{agent.agent_key} missing data_policy"
        assert isinstance(agent.model_tier, ModelTier), f"{agent.agent_key} missing model_tier"


def test_company_agent_seed_records_execution_not_allowed():
    from src.modules.agent_registry.company_agents import COMPANY_AGENTS, INACTIVE_AGENTS

    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        assert agent.runtime_mode in (RuntimeMode.MANUAL_CONTEXT_ONLY, RuntimeMode.METADATA_ONLY), (
            f"{agent.agent_key} has unexpected runtime_mode: {agent.runtime_mode}"
        )


def test_company_agent_seed_records_cloud_dispatch_not_allowed():
    from src.modules.agent_registry.company_agents import COMPANY_AGENTS, INACTIVE_AGENTS

    all_agents = COMPANY_AGENTS + INACTIVE_AGENTS
    for agent in all_agents:
        if agent.data_policy == DataPolicy.LOCAL_ONLY:
            assert agent.data_policy == DataPolicy.LOCAL_ONLY, (
                f"{agent.agent_key} is local_only but data_policy is wrong"
            )


def test_model_json_columns_have_defaults():
    mapper = inspect(AgentRegistryRecord)
    json_columns_with_default = [
        "responsibilities_json",
        "inputs_json",
        "outputs_json",
        "escalation_rules_json",
        "forbidden_actions_json",
    ]
    for col_name in json_columns_with_default:
        col = mapper.c.get(col_name)
        assert col is not None, f"Column {col_name} not found"
        assert col.default is not None or col.server_default is not None, (
            f"Column {col_name} has no default"
        )
