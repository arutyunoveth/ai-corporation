from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dry_run_zero_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Dry_Run_0_Entry_Criteria.md",
        LAUNCH_DIR / "Dry_Run_0_Scenario.md",
        LAUNCH_DIR / "Dry_Run_0_Execution_Log_Template.md",
        LAUNCH_DIR / "Dry_Run_0_Review_Template.md",
        LAUNCH_DIR / "Dry_Run_0_Success_Criteria.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing Dry Run 0 doc: {path.name}"


def test_readme_and_launch_docs_state_next_gate_is_dry_run_zero():
    readme_text = _read(REPO_ROOT / "README.md")
    criteria_text = _read(LAUNCH_DIR / "Dry_Run_0_Entry_Criteria.md")
    scenario_text = _read(LAUNCH_DIR / "Dry_Run_0_Scenario.md")
    restrictions_text = _read(LAUNCH_DIR / "Launch_L1_Restrictions.md")

    assert "The immediate next repository gate is `Dry Run 0`" in readme_text
    assert "`Dry Run 0` is the next step" in criteria_text
    assert "It is not a real pilot launch." in scenario_text
    assert "The immediate next execution gate before any real pilot remains `Dry Run 0`." in restrictions_text


def test_dry_run_zero_docs_do_not_claim_autonomous_behavior_or_pilot_already_launched():
    scenario_text = _read(LAUNCH_DIR / "Dry_Run_0_Scenario.md").lower()
    review_text = _read(LAUNCH_DIR / "Dry_Run_0_Review_Template.md").lower()
    success_text = _read(LAUNCH_DIR / "Dry_Run_0_Success_Criteria.md").lower()

    assert "not a real pilot launch" in scenario_text
    assert "go to controlled pilot l1" in review_text
    assert "no hidden dependency on reserved ai/runtime slots" in success_text.lower()


def test_reserved_and_deferred_modules_remain_honestly_classified_for_dry_run_zero():
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")
    criteria_text = _read(LAUNCH_DIR / "Dry_Run_0_Entry_Criteria.md")

    for token in [
        "| M-049 | Agent Registry |",
        "| M-050 | Prompt / Schema Library |",
        "| M-052 | Notification Layer |",
        "| M-053 | Red Flag Registry |",
        "| M-054 | Master Dashboard |",
        "| M-055 | SaaS Productization Tracker |",
    ]:
        assert token in mapping_text

    assert "`M-049` and `M-050` remain closed" in criteria_text
    assert "`M-052..M-055` remain documented as reconciled non-runtime slots" in criteria_text
