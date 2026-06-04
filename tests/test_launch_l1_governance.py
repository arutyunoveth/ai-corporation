from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_launch_l1_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Launch_Readiness_Gap_Audit.md",
        LAUNCH_DIR / "Launch_L1_Minimum_Baseline.md",
        LAUNCH_DIR / "Deferred_Modules_Risk_Assessment.md",
        LAUNCH_DIR / "Launch_L1_Go_NoGo_Checklist.md",
        LAUNCH_DIR / "Launch_L1_Restrictions.md",
        LAUNCH_DIR / "Launch_L1_Operator_Runbook.md",
        LAUNCH_DIR / "Launch_L1_Execution_Checklist.md",
        LAUNCH_DIR / "Launch_L1_Pilot_Playbook.md",
        LAUNCH_DIR / "Launch_L1_Control_Gates.md",
    ]

    for path in required_docs:
        assert path.exists(), f"Missing launch doc: {path.name}"


def test_launch_docs_and_readme_lock_operator_assisted_mode():
    readme_text = _read(REPO_ROOT / "README.md")
    audit_text = _read(LAUNCH_DIR / "Launch_Readiness_Gap_Audit.md")
    restrictions_text = _read(LAUNCH_DIR / "Launch_L1_Restrictions.md")
    runbook_text = _read(LAUNCH_DIR / "Launch_L1_Operator_Runbook.md")

    assert "operator-assisted" in readme_text
    assert "`GO with restrictions`" in audit_text
    assert "controlled pilot" in restrictions_text
    assert "human-assisted mode" in runbook_text


def test_launch_docs_do_not_claim_autonomous_or_self_serve_l1():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    audit_text = _read(LAUNCH_DIR / "Launch_Readiness_Gap_Audit.md").lower()
    restrictions_text = _read(LAUNCH_DIR / "Launch_L1_Restrictions.md").lower()
    pilot_text = _read(LAUNCH_DIR / "Launch_L1_Pilot_Playbook.md").lower()

    assert "controlled operator-assisted pilot" in readme_text
    assert "disallowed launch shape" in audit_text
    assert "must not be presented as" in restrictions_text
    assert "not meant to prove" in pilot_text


def test_reserved_and_reconciled_late_slots_remain_honest_in_launch_phase():
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")
    restrictions_text = _read(LAUNCH_DIR / "Launch_L1_Restrictions.md")
    audit_text = _read(LAUNCH_DIR / "Launch_Readiness_Gap_Audit.md")

    assert "| M-049 | Agent Registry |" in mapping_text
    assert "| M-050 | Prompt / Schema Library |" in mapping_text
    assert "| M-052 | Notification Layer |" in mapping_text
    assert "| M-053 | Red Flag Registry |" in mapping_text
    assert "| M-054 | Master Dashboard |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text

    for token in [
        "M-049 Agent Registry",
        "M-050 Prompt / Schema Library",
        "M-052 Notification Layer",
        "M-053 Red Flag Registry",
        "M-054 Master Dashboard",
        "M-055 SaaS Productization Tracker",
    ]:
        assert token in restrictions_text
        assert token in audit_text
