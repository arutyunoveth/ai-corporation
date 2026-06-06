from src.modules.event_log.models import DecisionRecord, EventRecord


def _prepare_demo_deal(client) -> dict:
    response = client.post(
        "/commercial-prebid-demo/run",
        json={"fixture_name": "commercial_mvp_demo", "provider": "stub"},
    )
    assert response.status_code == 201
    return response.json()


def _manual_tkp_payload() -> dict:
    return {
        "operator_ref": "commercial.operator",
        "suppliers": [
            {
                "legal_name": 'OOO "Electro Supply 1"',
                "display_name": "Electro Supply 1",
                "inn": "7701000001",
                "country_code": "RU",
                "contact_name": "Anna Supplier",
                "contact_email": "anna@example.test",
                "tags": ["ELECTRICAL_EQUIPMENT"],
                "quoted_amount": 1480000,
                "currency_code": "RUB",
                "notes": "Primary commercial option.",
            },
            {
                "legal_name": 'OOO "Electro Supply 2"',
                "display_name": "Electro Supply 2",
                "inn": "7701000002",
                "country_code": "RU",
                "contact_name": "Boris Supplier",
                "contact_email": "boris@example.test",
                "tags": ["ELECTRICAL_EQUIPMENT"],
                "quoted_amount": 1525000,
                "currency_code": "RUB",
                "notes": "Fallback commercial option.",
            },
        ],
    }


def test_commercial_bid_readiness_workspace_builds_tkp_economics_and_readiness(client, session):
    deal = _prepare_demo_deal(client)
    deal_id = deal["deal_id"]

    draft = client.post(
        f"/commercial-workspace/{deal_id}/supplier-request-draft",
        json={"operator_ref": "commercial.operator"},
    )
    assert draft.status_code == 201
    draft_payload = draft.json()
    assert "Manual TKP request draft" in draft_payload["request_subject"]
    assert draft_payload["supplier_questions"]

    tkp = client.post(
        f"/commercial-workspace/{deal_id}/tkp/register-manual-batch",
        json=_manual_tkp_payload(),
    )
    assert tkp.status_code == 201
    tkp_payload = tkp.json()
    assert len(tkp_payload["supplier_ids"]) == 2
    assert len(tkp_payload["quote_ids"]) == 2
    assert tkp_payload["quote_set_id"].startswith("QS-")

    readiness = client.post(
        f"/commercial-workspace/{deal_id}/readiness/build",
        json={"operator_ref": "commercial.operator"},
    )
    assert readiness.status_code == 201
    readiness_payload = readiness.json()
    assert readiness_payload["latest_ids"]["quote_comparison_set_id"]
    assert readiness_payload["economics_summary"]["finance_memo_set_id"]
    assert readiness_payload["readiness_summary"]["submission_readiness_status"] == "NOT_READY"
    assert "## Economics" in readiness_payload["executive_report_markdown"]
    assert "## Bid Readiness" in readiness_payload["executive_report_markdown"]

    action = client.post(
        f"/commercial-workspace/{deal_id}/actions",
        json={
            "action": "ready_for_human_submission",
            "operator_ref": "commercial.operator",
            "rationale": "Internal checks are complete; keep final submission human-controlled.",
            "approval_decision": "GO_WITH_CONDITIONS",
            "conditions": ["Manual submission only after final operator review."],
        },
    )
    assert action.status_code == 201
    action_payload = action.json()
    assert action_payload["submission_readiness_status"] in {"READY", "NEEDS_REVIEW"}

    snapshot = client.get(f"/commercial-workspace/{deal_id}")
    assert snapshot.status_code == 200
    snapshot_payload = snapshot.json()
    assert snapshot_payload["tkp_summary"]["quotes"]
    assert snapshot_payload["economics_summary"]["finance_memo_set_id"]
    assert snapshot_payload["readiness_summary"]["submission_readiness_status"] in {"READY", "NEEDS_REVIEW"}

    decision_codes = {
        item.decision_code for item in session.query(DecisionRecord).filter_by(deal_id=deal_id).all()
    }
    event_codes = {
        item.event_code for item in session.query(EventRecord).filter_by(deal_id=deal_id).all()
    }

    assert "COMMERCIAL_WORKSPACE_READY_FOR_HUMAN_SUBMISSION" in decision_codes
    assert "commercial_supplier_request_drafted" in event_codes
    assert "commercial_tkp_manual_registered" in event_codes
    assert "commercial_economics_built" in event_codes
    assert "commercial_bid_readiness_built" in event_codes
    assert "commercial_workspace_action_recorded" in event_codes


def test_commercial_bid_readiness_does_not_open_external_execution_paths(client, session):
    deal = _prepare_demo_deal(client)
    deal_id = deal["deal_id"]

    client.post(f"/commercial-workspace/{deal_id}/supplier-request-draft", json={"operator_ref": "commercial.operator"})
    client.post(f"/commercial-workspace/{deal_id}/tkp/register-manual-batch", json=_manual_tkp_payload())
    client.post(f"/commercial-workspace/{deal_id}/readiness/build", json={"operator_ref": "commercial.operator"})

    event_codes = {
        item.event_code for item in session.query(EventRecord).filter_by(deal_id=deal_id).all()
    }
    forbidden = {
        "external_execution_started",
        "external_execution_succeeded",
        "submission_execution_started",
        "submission_execution_submitted",
        "submission_attempt_recorded",
    }
    assert event_codes.isdisjoint(forbidden)
