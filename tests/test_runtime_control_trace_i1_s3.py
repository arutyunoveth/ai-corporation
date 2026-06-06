from pathlib import Path

from src.modules.event_log.models import EventRecord


REPO_ROOT = Path(__file__).resolve().parents[1]
RUNTIME_DOCS_DIR = REPO_ROOT / "docs" / "12_runtime_implementation"


def _build_agent_registry(client) -> str:
    response = client.post(
        "/agent-registry/build",
        json={
            "entries": [
                {
                    "agent_role_name": "Trace Reviewer",
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
                    "prompt_name": "trace-summary-v1",
                    "prompt_version": "v1",
                    "owner_operator": "Runtime Owner",
                    "reviewer_role": "Runtime Reviewer",
                    "prompt_purpose": "Traceable summary draft",
                    "input_schema_ref": "schemas/input.json",
                    "output_schema_ref": "schemas/output.json",
                    "validation_mode": "STRICT",
                    "allowed_use_contexts": ["PREBID_ANALYSIS"],
                    "forbidden_use_contexts": ["EXTERNAL_EXECUTION"],
                    "linked_agent_registry_ids": [agent_registry_id],
                    "asset_payload_json": {"template": "Draft summary"},
                }
            ]
        },
    )
    assert response.status_code == 201
    return response.json()["records"][0]["prompt_schema_id"]


def test_runtime_control_trace_can_be_created_and_reviewed(client, session):
    agent_registry_id = _build_agent_registry(client)
    prompt_schema_id = _build_prompt_schema(client, agent_registry_id)

    create_response = client.post(
        "/runtime-control-traces",
        json={
            "runtime_slice": "MVP_RUNTIME_PHASE_1",
            "source_entity": "demo_tender",
            "actor_type": "AGENT_PROFILE",
            "actor_ref": agent_registry_id,
            "action_type": "GENERATE_DRAFT",
            "target_module": "M-050",
            "target_record_id": prompt_schema_id,
            "prompt_schema_ref": prompt_schema_id,
            "agent_profile_ref": agent_registry_id,
            "input_artifact_ref": "ART-2026-000001",
            "output_artifact_ref": "ART-2026-000002",
            "input_summary": "Tender documents loaded.",
            "output_summary": "Draft summary prepared for review.",
            "validation_status": "PASSED",
            "human_review_status": "needs_human_review",
        },
    )
    assert create_response.status_code == 201
    trace = create_response.json()

    assert trace["prompt_schema_ref"] == prompt_schema_id
    assert trace["agent_profile_ref"] == agent_registry_id
    assert trace["validation_status"] == "PASSED"
    assert trace["human_review_status"] == "needs_human_review"

    update_response = client.patch(
        f"/runtime-control-traces/{trace['runtime_trace_id']}/review-status",
        json={
            "human_review_status": "approved_for_internal_use",
            "reviewer_operator": "Operator One",
            "final_disposition": "APPROVED_FOR_INTERNAL_USE",
        },
    )
    assert update_response.status_code == 200
    updated_trace = update_response.json()
    event_codes = {event.event_code for event in session.query(EventRecord).all()}

    assert updated_trace["human_review_status"] == "approved_for_internal_use"
    assert updated_trace["reviewer_operator"] == "Operator One"
    assert updated_trace["final_disposition"] == "APPROVED_FOR_INTERNAL_USE"
    assert "runtime_control_trace_created" in event_codes
    assert "runtime_control_trace_review_status_changed" in event_codes


def test_runtime_control_trace_list_and_boundaries_are_explicit(client):
    response = client.get("/runtime-control-traces")
    assert response.status_code == 200

    sprint_doc = RUNTIME_DOCS_DIR / "MVP_Runtime_I1_S3_Control_Trace_Ledger.md"
    backlog_doc = RUNTIME_DOCS_DIR / "Runtime_Backlog.md"
    sprint_text = sprint_doc.read_text(encoding="utf-8")
    backlog_text = backlog_doc.read_text(encoding="utf-8")

    for token in [
        "no actual autonomous execution",
        "no LLM calls",
        "no external action",
        "no automatic business-state advancement",
        "no tender submission",
    ]:
        assert token in sprint_text

    assert "I1-S4" in backlog_text
    assert "/runtime-control-traces" in client.app.openapi()["paths"]
