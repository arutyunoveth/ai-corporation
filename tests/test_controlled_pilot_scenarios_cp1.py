import json
from pathlib import Path

from src.modules.event_log.models import EventRecord


ROOT = Path(__file__).resolve().parents[1]
SCENARIO_DIR = ROOT / "fixtures" / "pilot_tenders"


def _scenario_names() -> list[str]:
    return sorted(path.stem for path in SCENARIO_DIR.glob("*.json"))


def test_controlled_pilot_scenario_pack_files_exist():
    names = _scenario_names()
    assert names == [
        "controlled_pilot_no_go_review",
        "controlled_pilot_risky_contract",
        "controlled_pilot_simple_relevant",
        "controlled_pilot_tkp_economics",
    ]

    for name in names:
        payload = json.loads((SCENARIO_DIR / f"{name}.json").read_text(encoding="utf-8"))
        assert payload["scenario_id"].startswith("CP-SC-")
        assert payload["expected_decision_notes"]["acceptable_preliminary_recommendations"]
        assert payload["expected_risk_categories"]


def test_controlled_pilot_scenarios_run_through_stub_pipeline(client, session):
    for name in _scenario_names():
        fixture = json.loads((SCENARIO_DIR / f"{name}.json").read_text(encoding="utf-8"))
        response = client.post(
            "/commercial-prebid-demo/run",
            json={"fixture_name": name, "provider": "stub"},
        )
        assert response.status_code == 201
        payload = response.json()

        assert payload["fixture_name"] == name
        assert payload["analysis_mode"] == "llm_controlled_stub"
        assert payload["report_json"]["summary"]["procurement_number"] == fixture["tender"]["source_procurement_number"]
        assert payload["report_json"]["preliminary_recommendation"] in fixture["expected_decision_notes"]["acceptable_preliminary_recommendations"]

        event_codes = {
            event.event_code
            for event in session.query(EventRecord).filter_by(deal_id=payload["deal_id"]).all()
        }
        assert "commercial_prebid_demo_started" in event_codes
        assert "commercial_prebid_demo_report_built" in event_codes
        assert "external_execution_started" not in event_codes
        assert "submission_execution_submitted" not in event_codes
