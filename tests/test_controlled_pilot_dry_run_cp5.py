import json

from sqlalchemy.orm import sessionmaker

from src.modules.controlled_pilot_dry_run.service import run_controlled_pilot_dry_run


def test_controlled_pilot_dry_run_produces_reports_and_evidence(session, tmp_path):
    testing_session_local = sessionmaker(
        bind=session.get_bind(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    summary = run_controlled_pilot_dry_run(
        testing_session_local,
        fixture_names=[
            "controlled_pilot_simple_relevant",
            "controlled_pilot_risky_contract",
        ],
        output_dir=tmp_path,
        provider="stub",
        operator_ref="pilot.operator",
    )

    assert summary.completed_scenarios == 1
    assert summary.blocked_scenarios == 1

    summary_json = tmp_path / "controlled_pilot_dry_run_summary.json"
    summary_markdown = tmp_path / "controlled_pilot_dry_run_summary.md"
    assert summary_json.exists()
    assert summary_markdown.exists()

    payload = json.loads(summary_json.read_text(encoding="utf-8"))
    assert payload["provider_mode"] == "stub"
    assert len(payload["scenario_results"]) == 2
    for result in payload["scenario_results"]:
        assert result["evidence_json_path"].endswith("_pilot_evidence.json")
        assert result["evidence_markdown_path"].endswith("_pilot_evidence.md")
        assert "submission_execution_started" not in json.dumps(result)


def test_controlled_pilot_dry_run_docs_exist():
    template_text = open("docs/product/Controlled_Pilot_Dry_Run_Result_Template.md", encoding="utf-8").read()
    sample_text = open("docs/product/samples/Controlled_Pilot_Dry_Run_Sample_Result.md", encoding="utf-8").read()

    assert "no autonomous bid submission" in template_text
    assert "no supplier outreach was sent" in sample_text
