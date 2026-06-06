from pathlib import Path

from src.modules.event_log.models import EventRecord


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DOCS_DIR = REPO_ROOT / "docs" / "12_runtime_implementation"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _build_agent_registry(client) -> str:
    response = client.post(
        "/agent-registry/build",
        json={
            "entries": [
                {
                    "agent_role_name": "Runtime Prompt Reviewer",
                    "capability_tags": ["GENERATE_DRAFT"],
                    "forbidden_action_classes": ["EXECUTE_EXTERNAL_ACTION"],
                    "owner_operator": "Runtime Owner",
                }
            ]
        },
    )
    assert response.status_code == 201
    return response.json()["records"][0]["agent_registry_id"]


def test_i1_s2_prompt_schema_metadata_accepts_updated_roadmap_vocabulary(client, session):
    agent_registry_id = _build_agent_registry(client)

    response = client.post(
        "/prompt-schema-library/build",
        json={
            "assets": [
                {
                    "prompt_name": "prebid-summary-v1",
                    "prompt_version": "v1",
                    "prompt_purpose": "Tender summary extraction",
                    "associated_runtime_slice": "MVP_RUNTIME_PHASE_1",
                    "input_schema_ref": "schemas/prebid-summary-input.json",
                    "output_schema_ref": "schemas/prebid-summary-output.json",
                    "validation_mode": "STRICT",
                    "review_status": "approved_for_internal_use",
                    "allowed_use_contexts": ["PREBID_ANALYSIS"],
                    "forbidden_use_contexts": ["EXTERNAL_EXECUTION"],
                    "human_review_required": True,
                    "notes": "bounded internal prompt metadata",
                    "rationale": "No prompt execution in this sprint.",
                    "owner_operator": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                    "asset_type": "PROMPT_TEMPLATE",
                    "risk_class": "MEDIUM",
                    "linked_agent_registry_ids": [agent_registry_id],
                    "asset_payload_json": {"template": "Summarize tender for internal review."},
                }
            ]
        },
    )
    assert response.status_code == 201

    payload = response.json()
    record = payload["records"][0]
    event_codes = {event.event_code for event in session.query(EventRecord).all()}

    assert record["prompt_name"] == "prebid-summary-v1"
    assert record["prompt_version"] == "v1"
    assert record["prompt_purpose"] == "Tender summary extraction"
    assert record["associated_runtime_slice"] == "MVP_RUNTIME_PHASE_1"
    assert record["validation_mode"] == "STRICT"
    assert record["review_status"] == "approved_for_internal_use"
    assert record["allowed_use_contexts"] == ["PREBID_ANALYSIS"]
    assert record["forbidden_use_contexts"] == ["EXTERNAL_EXECUTION"]
    assert record["human_review_required"] is True
    assert record["rationale"] == "No prompt execution in this sprint."
    assert record["agent_links"][0]["agent_registry_id"] == agent_registry_id
    assert "prompt_schema_record_created" in event_codes
    assert "agent_prompt_link_created" in event_codes


def test_i1_s2_prompt_schema_metadata_rejects_overlapping_contexts(client):
    response = client.post(
        "/prompt-schema-library/build",
        json={
            "assets": [
                {
                    "prompt_name": "bad-contexts",
                    "prompt_version": "v1",
                    "owner_operator": "Runtime Owner",
                    "allowed_use_contexts": ["PREBID_ANALYSIS"],
                    "forbidden_use_contexts": ["PREBID_ANALYSIS"],
                    "input_schema_ref": "schemas/input.json",
                    "asset_payload_json": {"template": "invalid"},
                }
            ]
        },
    )
    assert response.status_code == 422
    assert "overlapping allowed and forbidden use contexts" in str(response.json())


def test_i1_s2_docs_and_boundaries_are_explicit():
    sprint_doc = RUNTIME_DOCS_DIR / "MVP_Runtime_I1_S2_Prompt_Schema_Metadata_Library.md"
    backlog_doc = RUNTIME_DOCS_DIR / "Runtime_Backlog.md"

    assert sprint_doc.exists()
    assert backlog_doc.exists()

    sprint_text = _read(sprint_doc)
    backlog_text = _read(backlog_doc)

    for token in [
        "no live LLM provider calls",
        "no prompt execution",
        "no autonomous agents",
        "no external actions",
        "no tender submission",
    ]:
        assert token in sprint_text

    assert "Optional later" in backlog_text
