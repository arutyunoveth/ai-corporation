from pathlib import Path

from tests.test_dry_run_zero_execution import _execute_dry_run_zero


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_broader_internal_usage_wave_one_executes_multiple_controlled_internal_deals(client, session):
    first = _execute_dry_run_zero(client, session)
    second = _execute_dry_run_zero(client, session)

    assert first["intake"]["deal_id"]
    assert second["intake"]["deal_id"]
    assert first["claim"]["claim_trigger_set_id"]
    assert second["claim"]["claim_trigger_set_id"]
    assert first["launch_visibility"]["launch_visibility_set_id"] != second["launch_visibility"]["launch_visibility_set_id"]
    assert first["workspace"]["workspace_feed_set_id"] != second["workspace"]["workspace_feed_set_id"]
    assert first["action_queue"]["action_queue_set_id"] != second["action_queue"]["action_queue_set_id"]


def test_broader_internal_usage_wave_one_docs_exist_and_state_go_to_wave_two():
    required_docs = [
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_1_Execution_Log_Filled.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_1_Review_Result.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_1_Blockers_and_NonBlockers.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_1_Operator_Load_Notes.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing B1-S2 deliverable: {path.name}"

    readme_text = _read(REPO_ROOT / "README.md")
    review_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Wave_1_Review_Result.md")
    blockers_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Wave_1_Blockers_and_NonBlockers.md")

    assert "Broader Internal Usage Wave #1 has now been executed with explicit review output." in readme_text
    assert "`GO to wave #2`" in review_text
    assert "`GO to wave #2`" in blockers_text
