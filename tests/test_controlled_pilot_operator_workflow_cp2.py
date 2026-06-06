from pathlib import Path

from src.modules.event_log.models import DecisionRecord, EventRecord


DOCS_DIR = Path("docs/product")


def _prepare_demo_deal(client, fixture_name: str = "controlled_pilot_tkp_economics") -> dict:
    response = client.post(
        "/commercial-prebid-demo/run",
        json={"fixture_name": fixture_name, "provider": "stub"},
    )
    assert response.status_code == 201
    return response.json()


def _manual_tkp_payload() -> dict:
    return {
        "operator_ref": "pilot.operator",
        "suppliers": [
            {
                "legal_name": 'OOO "Pilot Supply 1"',
                "display_name": "Pilot Supply 1",
                "inn": "7702000001",
                "country_code": "RU",
                "contact_name": "Anna Pilot",
                "contact_email": "anna.pilot@example.test",
                "quoted_amount": 1495000,
                "currency_code": "RUB",
            },
            {
                "legal_name": 'OOO "Pilot Supply 2"',
                "display_name": "Pilot Supply 2",
                "inn": "7702000002",
                "country_code": "RU",
                "contact_name": "Boris Pilot",
                "contact_email": "boris.pilot@example.test",
                "quoted_amount": 1530000,
                "currency_code": "RUB",
            },
        ],
    }


def test_pilot_operator_docs_cover_controlled_workflow_states():
    checklist = (DOCS_DIR / "Pilot_Operator_Checklist.md").read_text(encoding="utf-8")
    error_handling = (DOCS_DIR / "Pilot_Operator_Error_Handling.md").read_text(encoding="utf-8")
    console_doc = (DOCS_DIR / "Operator_Console_Commercial_Skeleton.md").read_text(encoding="utf-8")

    for marker in [
        "`imported`",
        "`analyzed`",
        "`needs_review`",
        "`collect_tkp`",
        "`economics_review`",
        "`bid_readiness_review`",
        "`ready_for_human_submission`",
        "`rejected`",
    ]:
        assert marker in checklist

    assert "Never treat `ready_for_human_submission` as actual submission." in checklist
    assert "Never send supplier messages automatically from the repository." in checklist
    assert "critical" in error_handling
    assert "no submission" in console_doc


def test_operator_console_accepts_only_allowed_manual_control_actions(client, session):
    deal = _prepare_demo_deal(client, fixture_name="controlled_pilot_simple_relevant")
    deal_id = deal["deal_id"]

    action_map = {
        "rejected": "OPERATOR_REJECTED_PREBID",
        "needs_more_review": "OPERATOR_MARKED_NEEDS_MORE_REVIEW",
        "collect_tkp": "OPERATOR_MARKED_COLLECT_TKP",
        "prepare_bid_draft": "OPERATOR_MARKED_PREPARE_BID_DRAFT",
    }

    for action, decision_code in action_map.items():
        response = client.post(
            f"/commercial-console/deals/{deal_id}/actions",
            json={
                "action": action,
                "operator_ref": "pilot.operator",
                "rationale": f"Record {action} for controlled pilot flow.",
            },
        )
        assert response.status_code == 201
        payload = response.json()
        decision = session.query(DecisionRecord).filter_by(decision_id=payload["decision_id"]).one()
        event = session.query(EventRecord).filter_by(event_id=payload["recorded_event_id"]).one()
        assert decision.decision_code == decision_code
        assert event.event_code == "commercial_operator_action_recorded"
        assert event.payload_json["action"] == action

    invalid = client.post(
        f"/commercial-console/deals/{deal_id}/actions",
        json={
            "action": "auto_submit_bid",
            "operator_ref": "pilot.operator",
            "rationale": "This should never be accepted.",
        },
    )
    assert invalid.status_code == 422


def test_controlled_pilot_operator_path_stays_internal_and_human_reviewed(client, session):
    deal = _prepare_demo_deal(client)
    deal_id = deal["deal_id"]

    needs_review = client.post(
        f"/commercial-console/deals/{deal_id}/actions",
        json={
            "action": "needs_more_review",
            "operator_ref": "pilot.operator",
            "rationale": "Capture initial operator review before commercial progression.",
        },
    )
    assert needs_review.status_code == 201

    collect_tkp = client.post(
        f"/commercial-console/deals/{deal_id}/actions",
        json={
            "action": "collect_tkp",
            "operator_ref": "pilot.operator",
            "rationale": "Manual supplier pricing inputs are required.",
        },
    )
    assert collect_tkp.status_code == 201

    supplier_request = client.post(
        f"/commercial-workspace/{deal_id}/supplier-request-draft",
        json={"operator_ref": "pilot.operator"},
    )
    assert supplier_request.status_code == 201

    tkp_needed = client.post(
        f"/commercial-workspace/{deal_id}/actions",
        json={
            "action": "tkp_needed",
            "operator_ref": "pilot.operator",
            "rationale": "Track manual TKP collection state in the workspace.",
        },
    )
    assert tkp_needed.status_code == 201

    tkp_batch = client.post(
        f"/commercial-workspace/{deal_id}/tkp/register-manual-batch",
        json=_manual_tkp_payload(),
    )
    assert tkp_batch.status_code == 201

    tkp_received = client.post(
        f"/commercial-workspace/{deal_id}/actions",
        json={
            "action": "tkp_received",
            "operator_ref": "pilot.operator",
            "rationale": "Manual supplier quote inputs were reviewed and registered.",
        },
    )
    assert tkp_received.status_code == 201

    readiness = client.post(
        f"/commercial-workspace/{deal_id}/readiness/build",
        json={"operator_ref": "pilot.operator"},
    )
    assert readiness.status_code == 201

    economics_reviewed = client.post(
        f"/commercial-workspace/{deal_id}/actions",
        json={
            "action": "economics_reviewed",
            "operator_ref": "pilot.operator",
            "rationale": "Economics and readiness package reviewed internally.",
        },
    )
    assert economics_reviewed.status_code == 201

    ready = client.post(
        f"/commercial-workspace/{deal_id}/actions",
        json={
            "action": "ready_for_human_submission",
            "operator_ref": "pilot.operator",
            "rationale": "Internal checks complete; keep all external handling manual.",
            "approval_decision": "GO_WITH_CONDITIONS",
            "conditions": ["Manual human-controlled submission only outside this repository."],
        },
    )
    assert ready.status_code == 201
    ready_payload = ready.json()
    assert ready_payload["submission_readiness_status"] in {"READY", "NEEDS_REVIEW"}

    invalid_workspace = client.post(
        f"/commercial-workspace/{deal_id}/actions",
        json={
            "action": "submit_to_platform",
            "operator_ref": "pilot.operator",
            "rationale": "This should never be accepted.",
        },
    )
    assert invalid_workspace.status_code == 422

    decision_codes = {
        item.decision_code for item in session.query(DecisionRecord).filter_by(deal_id=deal_id).all()
    }
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

    assert {
        "OPERATOR_MARKED_NEEDS_MORE_REVIEW",
        "OPERATOR_MARKED_COLLECT_TKP",
        "COMMERCIAL_WORKSPACE_TKP_NEEDED",
        "COMMERCIAL_WORKSPACE_TKP_RECEIVED",
        "COMMERCIAL_WORKSPACE_ECONOMICS_REVIEWED",
        "COMMERCIAL_WORKSPACE_READY_FOR_HUMAN_SUBMISSION",
    }.issubset(decision_codes)
    assert {
        "commercial_operator_action_recorded",
        "commercial_workspace_action_recorded",
        "commercial_supplier_request_drafted",
        "commercial_tkp_manual_registered",
        "commercial_bid_readiness_built",
    }.issubset(event_codes)
    assert event_codes.isdisjoint(forbidden)
