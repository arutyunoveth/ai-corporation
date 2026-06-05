from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_broader_internal_usage_locked_package_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Broader_Internal_Usage_Master_Plan.md",
        LAUNCH_DIR / "Broader_Internal_Usage_S1_Internal_Usage_Wave_Setup.md",
        LAUNCH_DIR / "Broader_Internal_Usage_S2_Internal_Usage_Wave_1.md",
        LAUNCH_DIR / "Broader_Internal_Usage_S3_Internal_Usage_Wave_2_Stability_Check.md",
        LAUNCH_DIR / "Broader_Internal_Usage_S4_Review_Exit_Decision.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing broader internal usage locked doc: {path.name}"


def test_b1_s1_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_Charter.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Scope_Criteria.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Wave_Intake_Template.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Operator_Capacity_Rules.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Stop_Rules.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Review_Cadence.md",
        LAUNCH_DIR / "Broader_Internal_Usage_Decision_Log_Template.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing B1-S1 deliverable: {path.name}"


def test_readme_reflects_broader_internal_usage_final_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    charter_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Wave_Charter.md")
    sprint_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_S1_Internal_Usage_Wave_Setup.md")

    assert "Broader Internal Usage" in readme_text
    assert "Broader Internal Usage block completed." in readme_text
    assert "Final phase decision: `GO to broader internal steady-state usage`." in readme_text
    assert "operator-assisted" in charter_text
    assert "manual-control" in sprint_text


def test_reserved_and_deferred_slots_remain_honest_in_broader_internal_usage_s1():
    readme_text = _read(REPO_ROOT / "README.md")
    master_plan_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Master_Plan.md")
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

    assert "opening `M-049 / M-050`" in master_plan_text
    assert "declaring `M-052..M-055` as fully implemented runtime modules" in master_plan_text
    assert "Recommended next step: `continue broader internal steady-state usage under the same controlled restrictions`." in readme_text


def test_broader_internal_usage_s1_docs_do_not_claim_autonomous_or_external_launch():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    charter_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Wave_Charter.md").lower()
    scope_text = _read(LAUNCH_DIR / "Broader_Internal_Usage_Scope_Criteria.md").lower()

    assert "autonomous" in charter_text
    assert "broad public launch" in charter_text
    assert "external commercialization" in scope_text
    assert "steady-state usage" in readme_text
    assert "pilot launched" not in readme_text
