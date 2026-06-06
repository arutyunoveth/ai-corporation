from pathlib import Path

from src.modules.agent_registry.models import AgentRegistryRecord, AgentRegistrySet
from src.modules.event_log.models import EventRecord


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_build_agent_registry_and_persist_records(client, session):
    response = client.post(
        "/agent-registry/build",
        json={
            "registry_scope": "INTERNAL",
            "entries": [
                {
                    "agent_key": "ops-reviewer",
                    "agent_label": "Ops Reviewer",
                    "owner_role": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                    "activation_state": "REVIEWED",
                    "allowed_capabilities_json": ["LIST_METADATA"],
                    "blocked_capabilities_json": ["EXECUTE_AGENT"],
                },
                {
                    "agent_key": "ops-auditor",
                    "agent_label": "Ops Auditor",
                    "owner_role": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                    "activation_state": "DISABLED",
                    "allowed_capabilities_json": ["READ_AUDIT_LOG"],
                    "blocked_capabilities_json": ["EXECUTE_AGENT"],
                },
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    registry_set = session.query(AgentRegistrySet).filter_by(
        agent_registry_set_id=payload["agent_registry_set_id"]
    ).one()
    registry_records = session.query(AgentRegistryRecord).filter_by(
        agent_registry_set_id=payload["agent_registry_set_id"]
    ).all()

    assert registry_set.registry_scope == "INTERNAL"
    assert registry_set.registry_status == "BUILT"
    assert len(registry_records) == 2
    assert payload["records"][0]["prompt_links"] == []


def test_agent_registry_runtime_writes_bounded_events_and_docs_stay_honest(client, session):
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

    event_codes = {event.event_code for event in session.query(EventRecord).all()}
    assert "agent_registry_set_created" in event_codes
    assert "agent_registry_record_created" in event_codes
    assert "agent_registry_status_changed" in event_codes

    readme_text = _read(REPO_ROOT / "README.md")
    summary_text = _read(REPO_ROOT / "docs" / "00_architecture" / "implementation_summary_m049_bounded_runtime.md")

    assert "MVP Runtime Implementation — Phase 1 is now formally staged" in readme_text
    assert "bounded internal metadata registry contour" in summary_text
