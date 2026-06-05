from pathlib import Path

from tests.test_dry_run_zero_execution import _execute_dry_run_zero


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_optimization_cycle_one_runs_with_existing_manual_control_stack(client, session):
    package = _execute_dry_run_zero(client, session)

    assert package["workspace"]["workspace_feed_set_id"]
    assert package["action_queue"]["action_queue_set_id"]
    assert package["launch_visibility"]["launch_visibility_set_id"]
    assert package["knowledge_asset"]["knowledge_asset_set_id"]


def test_optimization_cycle_one_docs_exist_and_state_go_to_cycle_two():
    required_docs = [
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_1_Execution_Log_Filled.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_1_Review_Result.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_1_Blockers_and_NonBlockers.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_1_Friction_Deltas.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing O1-S2 deliverable: {path.name}"

    readme_text = _read(REPO_ROOT / "README.md")
    review_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_1_Review_Result.md")
    blockers_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Cycle_1_Blockers_and_NonBlockers.md")

    assert "Optimization Cycle #1 has now been executed with explicit review output." in readme_text
    assert "`GO to cycle #2`" in review_text
    assert "`GO to cycle #2`" in blockers_text
