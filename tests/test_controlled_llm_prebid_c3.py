from src.modules.runtime_control_traces.models import RuntimeControlTrace


def test_controlled_llm_stub_analysis_creates_validated_sections_and_traces(client, session):
    response = client.post(
        "/commercial-prebid-demo/run",
        json={"fixture_name": "commercial_mvp_demo", "provider": "stub"},
    )
    assert response.status_code == 201
    payload = response.json()

    assert payload["analysis_mode"] == "llm_controlled_stub"
    llm_analysis = payload["report_json"]["llm_analysis"]
    assert llm_analysis["overall_review_status"] == "needs_human_review"
    assert "tender_summary" in llm_analysis["sections"]
    assert llm_analysis["sections"]["bid_decision"]["validated_output"]["recommendation"] == "GO_WITH_CONDITIONS"

    trace_ids = llm_analysis["trace_ids"]
    traces = session.query(RuntimeControlTrace).filter(RuntimeControlTrace.runtime_trace_id.in_(trace_ids)).all()
    assert len(traces) == 5
    assert all(trace.prompt_schema_ref for trace in traces)
    assert all(trace.agent_profile_ref for trace in traces)
    assert all(trace.human_review_status in {"needs_human_review", "validation_failed"} for trace in traces)


def test_controlled_llm_invalid_output_stays_in_manual_review(client):
    response = client.post(
        "/commercial-prebid-demo/run",
        json={
            "fixture_name": "commercial_mvp_demo",
            "provider": "stub",
            "simulate_invalid_output": True,
        },
    )
    assert response.status_code == 201
    payload = response.json()

    assert payload["analysis_mode"] == "llm_controlled_stub"
    llm_analysis = payload["report_json"]["llm_analysis"]
    assert llm_analysis["sections"]["bid_decision"]["validation_status"] == "FAILED"
    assert llm_analysis["sections"]["bid_decision"]["review_status"] == "validation_failed"
    assert llm_analysis["overall_review_status"] == "needs_human_review"
