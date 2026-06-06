from pathlib import Path

from src.modules.runtime_control_traces.models import RuntimeControlTrace


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DOCS_DIR = REPO_ROOT / "docs" / "12_runtime_implementation"


def _build_agent_registry(client) -> str:
    response = client.post(
        "/agent-registry/build",
        json={
            "entries": [
                {
                    "agent_role_name": "Integrated Runtime Reviewer",
                    "capability_tags": ["GENERATE_DRAFT"],
                    "owner_operator": "Runtime Owner",
                }
            ]
        },
    )
    assert response.status_code == 201
    return response.json()["records"][0]["agent_registry_id"]


def _build_prompt_schema(client, agent_registry_id: str) -> str:
    response = client.post(
        "/prompt-schema-library/build",
        json={
            "assets": [
                {
                    "prompt_name": "slice-link-v1",
                    "prompt_version": "v1",
                    "owner_operator": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                    "prompt_purpose": "Metadata slice integration",
                    "input_schema_ref": "schemas/input.json",
                    "output_schema_ref": "schemas/output.json",
                    "allowed_use_contexts": ["PREBID_ANALYSIS"],
                    "forbidden_use_contexts": ["EXTERNAL_EXECUTION"],
                    "linked_agent_registry_ids": [agent_registry_id],
                    "asset_payload_json": {"template": "Link runtime metadata"},
                }
            ]
        },
    )
    assert response.status_code == 201
    return response.json()["records"][0]["prompt_schema_id"]


def _build_trace(client, agent_registry_id: str, prompt_schema_id: str) -> str:
    response = client.post(
        "/runtime-control-traces",
        json={
            "source_entity": "demo_tender",
            "actor_type": "AGENT_PROFILE",
            "actor_ref": agent_registry_id,
            "action_type": "GENERATE_DRAFT",
            "prompt_schema_ref": prompt_schema_id,
            "agent_profile_ref": agent_registry_id,
            "validation_status": "PASSED",
            "human_review_status": "needs_human_review",
        },
    )
    assert response.status_code == 201
    return response.json()["runtime_trace_id"]


def test_runtime_metadata_slice_links_agent_prompt_and_traces(client, session):
    agent_registry_id = _build_agent_registry(client)
    prompt_schema_id = _build_prompt_schema(client, agent_registry_id)
    trace_id = _build_trace(client, agent_registry_id, prompt_schema_id)

    response = client.post(
        "/runtime-metadata-slices",
        json={
            "linked_agent_profile_id": agent_registry_id,
            "linked_prompt_schema_id": prompt_schema_id,
            "allowed_runtime_contexts": ["PREBID_ANALYSIS"],
            "forbidden_runtime_contexts": ["EXTERNAL_EXECUTION"],
            "trace_refs": [trace_id],
            "notes": "bounded internal integration only",
        },
    )
    assert response.status_code == 201
    payload = response.json()

    assert payload["linked_agent_profile_id"] == agent_registry_id
    assert payload["linked_prompt_schema_id"] == prompt_schema_id
    assert payload["allowed_runtime_contexts"] == ["PREBID_ANALYSIS"]
    assert payload["forbidden_runtime_contexts"] == ["EXTERNAL_EXECUTION"]
    assert trace_id in payload["trace_refs"]
    assert len(payload["trace_refs"]) >= 2

    trace_count = session.query(RuntimeControlTrace).count()
    assert trace_count >= 2

    update_response = client.patch(
        f"/runtime-metadata-slices/{payload['runtime_metadata_slice_id']}/review-status",
        json={
            "review_status": "approved_for_internal_use",
            "notes": "Operator approved for internal-only usage.",
        },
    )
    assert update_response.status_code == 200
    assert update_response.json()["review_status"] == "approved_for_internal_use"


def test_runtime_metadata_slice_rejects_overlapping_contexts_and_docs_exist(client):
    bad_response = client.post(
        "/runtime-metadata-slices",
        json={
            "linked_agent_profile_id": "AR-2026-000001",
            "linked_prompt_schema_id": "PS-2026-000001",
            "allowed_runtime_contexts": ["PREBID_ANALYSIS"],
            "forbidden_runtime_contexts": ["PREBID_ANALYSIS"],
        },
    )
    assert bad_response.status_code == 422

    sprint_doc = RUNTIME_DOCS_DIR / "MVP_Runtime_I1_S4_Metadata_Slice_Integration.md"
    audit_doc = RUNTIME_DOCS_DIR / "MVP_Runtime_Phase_1_Final_Audit.md"
    completion_doc = RUNTIME_DOCS_DIR / "MVP_Runtime_Phase_1_Completion_Status.md"

    assert sprint_doc.exists()
    assert audit_doc.exists()
    assert completion_doc.exists()

    sprint_text = sprint_doc.read_text(encoding="utf-8")
    audit_text = audit_doc.read_text(encoding="utf-8")

    assert "no prompt execution" in sprint_text
    assert "no LLM provider calls" in sprint_text
    assert "no external action" in sprint_text
    assert "`GO to controlled LLM pre-bid analysis`" in audit_text
