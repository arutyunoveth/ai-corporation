from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_dry_run_zero_result_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Dry_Run_0_Execution_Log_Filled.md",
        LAUNCH_DIR / "Dry_Run_0_Review_Result.md",
        LAUNCH_DIR / "Dry_Run_0_Blockers_and_NonBlockers.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing Dry Run 0 result doc: {path.name}"


def test_dry_run_zero_review_contains_explicit_decision_and_current_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    review_text = _read(LAUNCH_DIR / "Dry_Run_0_Review_Result.md")
    checklist_text = _read(LAUNCH_DIR / "Launch_L1_Go_NoGo_Checklist.md")

    assert "`GO with minor fixes before L1`" in review_text
    assert "Dry Run 0 has been executed and reviewed" in checklist_text
    assert "Dry Run 0 has now been executed and reviewed." in readme_text
    assert "The immediate next repository gate is no longer Dry Run 0." in readme_text


def test_reserved_and_deferred_modules_remain_honest_after_dry_run_zero():
    review_text = _read(LAUNCH_DIR / "Dry_Run_0_Review_Result.md")
    blockers_text = _read(LAUNCH_DIR / "Dry_Run_0_Blockers_and_NonBlockers.md")
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

    assert "No reserved modules were opened." in review_text
    assert "No deferred runtime slot was reclassified as fully implemented." in review_text
    assert "M-049/M-050 remain reserved" in blockers_text
    assert "M-052..M-055 remain deferred non-runtime slots" in blockers_text


def test_post_dry_run_docs_do_not_claim_autonomous_launch():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    review_text = _read(LAUNCH_DIR / "Dry_Run_0_Review_Result.md").lower()

    assert "controlled pilot `l1`" in review_text
    assert "pilot launched" not in readme_text
    assert "autonomous tender submission" not in review_text
