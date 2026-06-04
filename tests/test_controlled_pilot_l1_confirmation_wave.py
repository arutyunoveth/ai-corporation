from pathlib import Path

from tests.test_dry_run_zero_execution import _execute_dry_run_zero


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_controlled_pilot_l1_confirmation_wave_repeats_without_new_blockers(client, session):
    first = _execute_dry_run_zero(client, session)
    second = _execute_dry_run_zero(client, session)

    assert first["intake"]["deal_id"]
    assert second["intake"]["deal_id"]
    assert first["claim"]["claim_trigger_set_id"]
    assert second["claim"]["claim_trigger_set_id"]
    assert first["launch_visibility"]["launch_visibility_set_id"] != second["launch_visibility"]["launch_visibility_set_id"]


def test_controlled_pilot_l1_confirmation_wave_docs_exist_and_point_to_s4():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_2_Execution_Log_Filled.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_2_Review_Result.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Confirmation_Wave_Analysis.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S3 deliverable: {path.name}"

    review_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Deal_2_Review_Result.md")
    analysis_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Confirmation_Wave_Analysis.md")

    assert "`Proceed to L1-S4 final review`" in review_text
    assert "`Controlled Pilot L1 confirmation wave completed`" in analysis_text
