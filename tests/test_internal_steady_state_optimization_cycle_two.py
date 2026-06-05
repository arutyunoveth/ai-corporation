from pathlib import Path

from tests.test_dry_run_zero_execution import _execute_dry_run_zero


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_optimization_cycle_two_confirms_repeatability_without_runtime_opening(client, session):
    first = _execute_dry_run_zero(client, session)
    second = _execute_dry_run_zero(client, session)

    assert first["workspace"]["workspace_feed_set_id"]
    assert second["workspace"]["workspace_feed_set_id"]
    assert first["launch_visibility"]["launch_visibility_set_id"] != second["launch_visibility"]["launch_visibility_set_id"]
    assert first["action_queue"]["action_queue_set_id"] != second["action_queue"]["action_queue_set_id"]


def test_optimization_cycle_two_docs_exist_and_point_to_s4():
    required_docs = [
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_2_Execution_Log_Filled.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_2_Review_Result.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Repeatability_Analysis.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing O1-S3 deliverable: {path.name}"

    readme_text = _read(REPO_ROOT / "README.md")
    review_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_2_Review_Result.md")
    analysis_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Repeatability_Analysis.md")

    assert "Optimization Cycle #2 has now been executed as a repeatability check." in readme_text
    assert "Internal Steady-State Optimization block completed." in readme_text
    assert "`Proceed to Optimization S4 final review`" in review_text
    assert "`Optimization repeatability check completed`" in analysis_text
