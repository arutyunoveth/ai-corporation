from src.modules.event_log.models import EventRecord


def test_run_commercial_prebid_demo_generates_customer_facing_report(client, session):
    response = client.post(
        "/commercial-prebid-demo/run",
        json={"fixture_name": "commercial_mvp_demo"},
    )
    assert response.status_code == 201
    payload = response.json()

    assert payload["analysis_mode"] == "deterministic"
    assert payload["report_json"]["preliminary_recommendation"] in {"GO", "GO_WITH_CONDITIONS", "NEEDS_REVIEW"}
    assert "## Tender Summary" in payload["report_markdown"]
    assert "## Technical Requirements" in payload["report_markdown"]
    assert "## Contract Risks" in payload["report_markdown"]
    assert "## Decision Recommendation" in payload["report_markdown"]
    assert payload["report_json"]["summary"]["procurement_number"] == "CGMA-2026-0615"

    event_codes = {
        event.event_code
        for event in session.query(EventRecord).filter_by(deal_id=payload["deal_id"]).all()
    }
    assert "commercial_prebid_demo_started" in event_codes
    assert "commercial_prebid_demo_report_built" in event_codes
    assert "external_execution_started" not in event_codes
    assert "submission_execution_submitted" not in event_codes


def test_commercial_prebid_demo_docs_exist():
    import pathlib

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    required = [
        repo_root / "docs" / "product" / "Commercial_PreBid_Demo_Runbook.md",
        repo_root / "docs" / "product" / "Commercial_PreBid_Report_Spec.md",
        repo_root / "scripts" / "run_commercial_prebid_demo.py",
    ]
    for path in required:
        assert path.exists(), f"Missing C2 deliverable: {path.name}"
