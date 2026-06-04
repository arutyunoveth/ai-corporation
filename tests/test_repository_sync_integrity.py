from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_repository_sync_integrity_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Repository_Sync_Integrity_Report.md",
        LAUNCH_DIR / "Dry_Run_0_Entry_Criteria.md",
        LAUNCH_DIR / "Repository_Public_State_Checklist.md",
        LAUNCH_DIR / "Launch_Readiness_Gap_Audit.md",
        LAUNCH_DIR / "Launch_L1_Minimum_Baseline.md",
        LAUNCH_DIR / "Launch_L1_Go_NoGo_Checklist.md",
        LAUNCH_DIR / "Launch_L1_Operator_Runbook.md",
        LAUNCH_DIR / "Launch_L1_Execution_Checklist.md",
        LAUNCH_DIR / "Launch_L1_Pilot_Playbook.md",
        LAUNCH_DIR / "Launch_L1_Control_Gates.md",
        LAUNCH_DIR / "Launch_L1_Restrictions.md",
        LAUNCH_DIR / "Pre_L1_Ops_Visibility_Package.md",
        LAUNCH_DIR / "Pre_L1_Attention_and_Red_Flags.md",
        LAUNCH_DIR / "Pre_L1_Owner_Overview.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing integrity/launch doc: {path.name}"


def test_readme_and_integrity_docs_state_dry_run_zero_truth():
    readme_text = _read(REPO_ROOT / "README.md")
    report_text = _read(LAUNCH_DIR / "Repository_Sync_Integrity_Report.md")
    criteria_text = _read(LAUNCH_DIR / "Dry_Run_0_Entry_Criteria.md")

    assert "The immediate next repository gate is `Dry Run 0`" in readme_text
    assert "`repository ready for Dry Run 0`" in report_text
    assert "`Dry Run 0` is the next step" in criteria_text


def test_reserved_and_deferred_slots_remain_honestly_classified():
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")
    report_text = _read(LAUNCH_DIR / "Repository_Sync_Integrity_Report.md")
    checklist_text = _read(LAUNCH_DIR / "Repository_Public_State_Checklist.md")

    for token in [
        "| M-049 | Agent Registry |",
        "| M-050 | Prompt / Schema Library |",
        "| M-052 | Notification Layer |",
        "| M-053 | Red Flag Registry |",
        "| M-054 | Master Dashboard |",
        "| M-055 | SaaS Productization Tracker |",
    ]:
        assert token in mapping_text

    assert "no false runtime claim" in checklist_text
    assert "recovery-complete for the non-AI business skeleton" in report_text
    assert "not yet claiming" in report_text
