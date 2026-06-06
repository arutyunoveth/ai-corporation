from src.modules.event_log.models import DecisionRecord, EventRecord


def _prepare_demo_deal(client) -> str:
    payload = client.post(
        "/commercial-prebid-demo/run",
        json={"fixture_name": "commercial_mvp_demo", "provider": "stub"},
    ).json()
    return payload["deal_id"]


def test_commercial_operator_console_views_render_for_demo_deal(client):
    deal_id = _prepare_demo_deal(client)

    dashboard = client.get("/commercial-console")
    tender_card = client.get(f"/commercial-console/deals/{deal_id}")
    report = client.get(f"/commercial-console/deals/{deal_id}/report")
    requirements = client.get(f"/commercial-console/deals/{deal_id}/requirements")
    risks = client.get(f"/commercial-console/deals/{deal_id}/risks")
    traces = client.get(f"/commercial-console/deals/{deal_id}/runtime-traces")
    decision = client.get(f"/commercial-console/deals/{deal_id}/decision")

    assert dashboard.status_code == 200
    assert "Commercial Operator Dashboard" in dashboard.text
    assert tender_card.status_code == 200 and deal_id in tender_card.text
    assert report.status_code == 200 and "Pre-Bid Report View" in report.text
    assert requirements.status_code == 200 and "Requirements" in requirements.text
    assert risks.status_code == 200 and "Risks" in risks.text
    assert traces.status_code == 200 and "Runtime Trace Review" in traces.text
    assert decision.status_code == 200 and "Decision Action View" in decision.text


def test_commercial_operator_console_action_records_event_and_decision(client, session):
    deal_id = _prepare_demo_deal(client)

    response = client.post(
        f"/commercial-console/deals/{deal_id}/actions",
        json={
            "action": "collect_tkp",
            "operator_ref": "commercial.operator",
            "rationale": "Need supplier commercial inputs before bid drafting.",
        },
    )
    assert response.status_code == 201
    payload = response.json()

    decision = session.query(DecisionRecord).filter_by(decision_id=payload["decision_id"]).one()
    event = session.query(EventRecord).filter_by(event_id=payload["recorded_event_id"]).one()

    assert decision.decision_code == "OPERATOR_MARKED_COLLECT_TKP"
    assert event.event_code == "commercial_operator_action_recorded"
    assert event.payload_json["action"] == "collect_tkp"
