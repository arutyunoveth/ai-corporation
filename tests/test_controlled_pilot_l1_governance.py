from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_controlled_pilot_l1_locked_package_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Master_Plan.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_S1_Pilot_Wave_Setup.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_S2_Pilot_Deal_1_Execution.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_S3_Pilot_Deal_2_Execution.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_S4_Pilot_Review_Exit_Decision.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing controlled pilot locked doc: {path.name}"


def test_s1_pilot_wave_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Wave_Charter.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_Selection_Criteria.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_Intake_Template.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Stop_Rules.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Review_Cadence.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Decision_Log_Template.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S1 deliverable: {path.name}"


def test_readme_reflects_current_controlled_pilot_phase_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    charter_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Wave_Charter.md")
    sprint_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_S1_Pilot_Wave_Setup.md")

    assert "Controlled Pilot L1" in readme_text
    assert "operator-assisted" in charter_text
    assert "manual-control" in sprint_text
    assert "Controlled Pilot L1 block completed" in readme_text


def test_s2_pilot_deal_one_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Execution_Log_Filled.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Review_Result.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Blockers_and_NonBlockers.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S2 deliverable: {path.name}"


def test_s3_confirmation_wave_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_2_Execution_Log_Filled.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Deal_2_Review_Result.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Confirmation_Wave_Analysis.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S3 deliverable: {path.name}"


def test_s4_exit_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Final_Review.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Exit_Decision.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Post_Pilot_Recommendations.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S4 deliverable: {path.name}"


def test_reserved_and_deferred_slots_remain_honest_in_controlled_pilot_s1():
    readme_text = _read(REPO_ROOT / "README.md")
    master_plan_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Master_Plan.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    for token in [
        "| M-049 | Agent Registry |",
        "| M-050 | Prompt / Schema Library |",
        "| M-052 | Notification Layer |",
        "| M-053 | Red Flag Registry |",
        "| M-054 | Master Dashboard |",
        "| M-055 | SaaS Productization Tracker |",
    ]:
        assert token in mapping_text

    assert "opening `M-049` / `M-050`" in master_plan_text
    assert "declaring `M-052..M-055` as fully implemented runtime modules" in master_plan_text
    assert "Controlled Pilot L1 block completed" in readme_text


def test_controlled_pilot_s1_docs_do_not_claim_autonomous_or_broad_launch():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    charter_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Wave_Charter.md").lower()
    selection_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Deal_Selection_Criteria.md").lower()
    review_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Deal_1_Review_Result.md").lower()
    confirmation_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Confirmation_Wave_Analysis.md").lower()
    exit_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Exit_Decision.md").lower()

    assert "autonomous" in charter_text
    assert "broad launch" in selection_text
    assert "controlled pilot l1 block completed" in readme_text
    assert "go to deal #2" in review_text
    assert "go with restrictions" in confirmation_text
    assert "go with restrictions" in exit_text
    assert "pilot launched" not in readme_text
