from pathlib import Path

from src.modules.agent_registry.models import AgentRegistryRecord, AgentRegistrySet
from src.modules.prompt_schema_library.models import AgentPromptLink, PromptSchemaLibrarySet, PromptSchemaRecord
from src.shared.enums import (
    AgentActivationState,
    AgentPromptLinkStatus,
    AgentRegistryStatus,
    PromptSchemaAssetStatus,
    PromptSchemaAssetType,
    PromptSchemaLibraryStatus,
)
from src.shared.ids import (
    next_agent_registry_id,
    next_agent_registry_set_id,
    next_prompt_schema_id,
    next_prompt_schema_library_set_id,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mvp_phase_1_foundation_models_persist(session):
    agent_set = AgentRegistrySet(
        agent_registry_set_id=next_agent_registry_set_id(session, AgentRegistrySet.agent_registry_set_id),
        registry_scope="INTERNAL",
        registry_status=AgentRegistryStatus.BUILT,
    )
    prompt_set = PromptSchemaLibrarySet(
        prompt_schema_library_set_id=next_prompt_schema_library_set_id(
            session,
            PromptSchemaLibrarySet.prompt_schema_library_set_id,
        ),
        library_scope="INTERNAL",
        library_status=PromptSchemaLibraryStatus.BUILT,
    )
    session.add(agent_set)
    session.add(prompt_set)
    session.flush()

    agent = AgentRegistryRecord(
        agent_registry_id=next_agent_registry_id(session, AgentRegistryRecord.agent_registry_id),
        agent_registry_set_id=agent_set.agent_registry_set_id,
        agent_key="ops-reviewer",
        agent_label="Ops Reviewer",
        owner_role="Runtime Owner",
        reviewer_role="Runtime Reviewer",
        activation_state=AgentActivationState.REVIEWED,
        allowed_capabilities_json=["LIST_METADATA"],
        blocked_capabilities_json=["EXECUTE_AGENT"],
    )
    prompt = PromptSchemaRecord(
        prompt_schema_id=next_prompt_schema_id(session, PromptSchemaRecord.prompt_schema_id),
        prompt_schema_library_set_id=prompt_set.prompt_schema_library_set_id,
        asset_key="ops-reviewer-summary",
        asset_type=PromptSchemaAssetType.PROMPT_TEMPLATE,
        version_tag="v1",
        owner_role="Runtime Owner",
        reviewer_role="Runtime Reviewer",
        asset_status=PromptSchemaAssetStatus.REVIEWED,
        usage_constraints_text="Internal metadata only.",
        asset_payload_json={"template": "Summarize internal metadata."},
    )
    session.add(agent)
    session.add(prompt)
    session.flush()
    session.add(
        AgentPromptLink(
            agent_registry_id=agent.agent_registry_id,
            prompt_schema_id=prompt.prompt_schema_id,
            link_status=AgentPromptLinkStatus.APPROVED,
        )
    )
    session.commit()

    assert session.query(AgentRegistrySet).count() == 1
    assert session.query(PromptSchemaLibrarySet).count() == 1
    assert session.query(AgentRegistryRecord).count() == 1
    assert session.query(PromptSchemaRecord).count() == 1
    assert session.query(AgentPromptLink).count() == 1


def test_foundation_summary_and_readme_reflect_bounded_phase():
    summary_text = (REPO_ROOT / "docs" / "00_architecture" / "implementation_summary_mvp_phase_1_foundation.md").read_text(
        encoding="utf-8"
    )
    readme_text = (REPO_ROOT / "README.md").read_text(encoding="utf-8")

    assert "bounded technical base" in summary_text
    assert "Current phase status: `repository ready for MVP runtime slice definition`." in readme_text
