from pathlib import Path

from src.modules.agent_registry.models import AgentRegistryRecord
from src.modules.event_log.models import EventRecord
from src.modules.prompt_schema_library.models import AgentPromptLink, PromptSchemaLibrarySet, PromptSchemaRecord


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_agent_registry(client) -> str:
    response = client.post(
        "/agent-registry/build",
        json={
            "entries": [
                {
                    "agent_key": "ops-reviewer",
                    "agent_label": "Ops Reviewer",
                    "owner_role": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                }
            ]
        },
    )
    assert response.status_code == 201
    return response.json()["records"][0]["agent_registry_id"]


def test_build_prompt_schema_library_and_persist_links(client, session):
    agent_registry_id = _build_agent_registry(client)

    response = client.post(
        "/prompt-schema-library/build",
        json={
            "library_scope": "INTERNAL",
            "assets": [
                {
                    "asset_key": "ops-reviewer-summary",
                    "asset_type": "PROMPT_TEMPLATE",
                    "version_tag": "v1",
                    "owner_role": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                    "usage_constraints_text": "Internal metadata only.",
                    "asset_payload_json": {"template": "Summarize agent metadata."},
                    "linked_agent_registry_ids": [agent_registry_id],
                }
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    library_set = session.query(PromptSchemaLibrarySet).filter_by(
        prompt_schema_library_set_id=payload["prompt_schema_library_set_id"]
    ).one()
    prompt_record = session.query(PromptSchemaRecord).filter_by(
        prompt_schema_library_set_id=payload["prompt_schema_library_set_id"]
    ).one()
    links = session.query(AgentPromptLink).filter_by(prompt_schema_id=prompt_record.prompt_schema_id).all()

    assert library_set.library_scope == "INTERNAL"
    assert library_set.library_status == "BUILT"
    assert len(links) == 1
    assert payload["records"][0]["agent_links"][0]["agent_registry_id"] == agent_registry_id


def test_prompt_schema_runtime_writes_events_and_links_back_to_agent_registry(client, session):
    agent_registry_id = _build_agent_registry(client)
    response = client.post(
        "/prompt-schema-library/build",
        json={
            "assets": [
                {
                    "asset_key": "ops-audit-schema",
                    "asset_type": "INPUT_SCHEMA",
                    "version_tag": "v1",
                    "owner_role": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                    "usage_constraints_text": "Audit input only.",
                    "asset_payload_json": {"schema": {"type": "object"}},
                    "linked_agent_registry_ids": [agent_registry_id],
                }
            ]
        },
    )
    assert response.status_code == 201
    prompt_schema_id = response.json()["records"][0]["prompt_schema_id"]

    event_codes = {event.event_code for event in session.query(EventRecord).all()}
    assert "prompt_schema_library_set_created" in event_codes
    assert "prompt_schema_record_created" in event_codes
    assert "agent_prompt_link_created" in event_codes
    assert "prompt_schema_status_changed" in event_codes

    agent_record = session.query(AgentRegistryRecord).filter_by(agent_registry_id=agent_registry_id).one()
    agent_response = client.get(f"/agent-registry/records/{agent_record.agent_registry_id}")
    assert agent_response.status_code == 200
    assert agent_response.json()["prompt_links"][0]["prompt_schema_id"] == prompt_schema_id

    readme_text = _read(REPO_ROOT / "README.md")
    summary_text = _read(REPO_ROOT / "docs" / "00_architecture" / "implementation_summary_m050_bounded_runtime.md")

    assert "M-050 bounded runtime slice implemented." in readme_text
    assert "no prompt execution runtime" in summary_text
