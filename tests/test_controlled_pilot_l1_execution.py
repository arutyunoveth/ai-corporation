from pathlib import Path

from tests.test_dry_run_zero_execution import _execute_dry_run_zero


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_controlled_pilot_l1_deal_one_executes_end_to_end(client, session):
    package = _execute_dry_run_zero(client, session)

    assert package["comparison"]["quote_comparison_set_id"]
    assert package["supplier_contract"]["supplier_contract_set_id"]
    assert package["execution_plan"]["execution_plan_set_id"]
    assert package["purchase_order"]["purchase_order_set_id"]
    assert package["payment_tracking"]["payment_tracking_set_id"]
    assert package["claim"]["claim_trigger_set_id"]
    assert package["deal_closure_report"]["deal_closure_report_set_id"]
    assert package["postmortem"]["postmortem_set_id"]
    assert package["knowledge_asset"]["knowledge_asset_set_id"]
    assert package["launch_visibility"]["launch_visibility_set_id"]


def test_controlled_pilot_l1_deal_one_result_docs_exist_and_state_go_to_deal_two():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Execution_Log_Filled.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Review_Result.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Blockers_and_NonBlockers.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S2 deliverable: {path.name}"

    review_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Review_Result.md")
    blockers_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Blockers_and_NonBlockers.md")

    assert "`GO to deal #2`" in review_text
    assert "`GO to deal #2`" in blockers_text
