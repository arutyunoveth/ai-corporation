from pathlib import Path

from src.modules.event_log.models import EventRecord


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DOCS_DIR = REPO_ROOT / "docs" / "12_runtime_implementation"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_i1_s1_foundation_accepts_updated_roadmap_metadata_vocabulary(client, session):
    response = client.post(
        "/agent-registry/build",
        json={
            "entries": [
                {
                    "agent_role_name": "Ops Metadata Reviewer",
                    "capability_tags": ["LIST_METADATA"],
                    "forbidden_action_classes": ["EXECUTE_AGENT"],
                    "owner_operator": "Runtime Owner",
                    "description": "Metadata-only reviewer profile.",
                    "lifecycle_status": "REVIEWED",
                }
            ]
        },
    )
    assert response.status_code == 201

    payload = response.json()
    record = payload["records"][0]
    event_codes = {event.event_code for event in session.query(EventRecord).all()}

    assert record["agent_profile_id"] == record["agent_registry_id"]
    assert record["agent_role_name"] == "Ops Metadata Reviewer"
    assert record["description"] == "Metadata-only reviewer profile."
    assert record["capability_tags"] == ["LIST_METADATA"]
    assert record["allowed_action_classes"] == ["LIST_METADATA"]
    assert record["forbidden_action_classes"] == ["EXECUTE_AGENT"]
    assert record["owner_operator"] == "Runtime Owner"
    assert record["lifecycle_status"] == "REVIEWED"
    assert record["review_status"] == "approved_for_internal_use"
    assert "agent_registry_record_created" in event_codes


def test_i1_s1_foundation_docs_and_boundaries_are_explicit(client):
    sprint_doc = RUNTIME_DOCS_DIR / "MVP_Runtime_I1_S1_Agent_Metadata_Foundation.md"
    backlog_doc = RUNTIME_DOCS_DIR / "Runtime_Backlog.md"

    assert sprint_doc.exists()
    assert backlog_doc.exists()

    sprint_text = _read(sprint_doc)
    backlog_text = _read(backlog_doc)

    for token in [
        "no autonomous agent execution",
        "no LLM calls",
        "no external platform execution",
        "no tender submission",
        "no supplier communication automation",
    ]:
        assert token in sprint_text

    assert "Optional later" in backlog_text

    assert "/agent-registry/execute" not in client.app.openapi()["paths"]
