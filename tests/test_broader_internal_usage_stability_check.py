from pathlib import Path

from tests.test_dry_run_zero_execution import _execute_dry_run_zero


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_broader_internal_usage_stability_check_repeats_without_new_blockers(client, session):
    first = _execute_dry_run_zero(client, session)
    second = _execute_dry_run_zero(client, session)

    assert first["claim"]["claim_trigger_set_id"]
    assert second["claim"]["claim_trigger_set_id"]
    assert first["launch_visibility"]["launch_visibility_set_id"] != second["launch_visibility"]["launch_visibility_set_id"]
    assert first["action_queue"]["action_queue_set_id"] != second["action_queue"]["action_queue_set_id"]


def test_broader_internal_usage_stability_docs_exist_and_point_to_s4():
    required_docs = [
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_2_Execution_Log_Filled.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_2_Review_Result.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Stability_Check_Analysis.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing B1-S3 deliverable: {path.name}"

    readme_text = _read(REPO_ROOT / "README.md")
    review_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Wave_2_Review_Result.md")
    analysis_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Stability_Check_Analysis.md")

    assert "Broader Internal Usage Wave #2 has now been executed as a stability check." in readme_text
    assert "Current phase gate: `Proceed to B1-S4 final review`." in readme_text
    assert "`Proceed to B1-S4 final review`" in review_text
    assert "`Broader Internal Usage stability check completed`" in analysis_text
