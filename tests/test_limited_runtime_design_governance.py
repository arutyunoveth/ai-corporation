from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_limited_runtime_design_locked_package_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Limited_Runtime_Design_Master_Plan.md",
        LAUNCH_DIR / "Limited_Runtime_Design_S1_Scope_Safety_Rules.md",
        LAUNCH_DIR / "Limited_Runtime_Design_S2_M049_M050_Design.md",
        LAUNCH_DIR / "Limited_Runtime_Design_S3_M052_M055_Supporting_Design.md",
        LAUNCH_DIR / "Limited_Runtime_Design_S4_Review_Implementation_Gate.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing limited runtime design locked doc: {path.name}"


def test_limited_runtime_design_s1_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Limited_Runtime_Design_Charter.md",
        LAUNCH_DIR / "Limited_Runtime_Design_Constraints_Register.md",
        LAUNCH_DIR / "Limited_Runtime_Design_Safety_Rules.md",
        LAUNCH_DIR / "Limited_Runtime_Design_Non_Goals.md",
        LAUNCH_DIR / "Limited_Runtime_Design_Implementation_Prerequisites.md",
        LAUNCH_DIR / "Limited_Runtime_Design_Decision_Log_Template.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing D1-S1 deliverable: {path.name}"


def test_readme_reflects_limited_runtime_design_s1_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    charter_text = _read(LAUNCH_DIR / "Limited_Runtime_Design_Charter.md")
    sprint_text = _read(LAUNCH_DIR / "Limited_Runtime_Design_S1_Scope_Safety_Rules.md")

    assert "Limited Runtime Design" in readme_text
    assert "Limited Runtime Design is now formally staged under a locked master plan and S1 scope/safety package." in readme_text
    assert "Current phase status: `repository ready for limited runtime design work`." in readme_text
    assert "no hidden runtime opening" in charter_text
    assert "без opening M-049/M-050 in runtime" in sprint_text


def test_reserved_and_deferred_slots_remain_honest_in_limited_runtime_design_s1():
    readme_text = _read(REPO_ROOT / "README.md")
    master_plan_text = _read(LAUNCH_DIR / "Limited_Runtime_Design_Master_Plan.md")
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

    assert "runtime implementation of M-049/M-050" in master_plan_text
    assert "activation of M-052..M-055 as working runtime" in master_plan_text
    assert "Current phase status: `repository ready for limited runtime design work`." in readme_text


def test_limited_runtime_design_s1_docs_do_not_claim_runtime_completion():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    charter_text = _read(LAUNCH_DIR / "Limited_Runtime_Design_Charter.md").lower()
    non_goals_text = _read(LAUNCH_DIR / "Limited_Runtime_Design_Non_Goals.md").lower()

    assert "runtime implementation" in charter_text
    assert "implementing `m-049 agent registry`" in non_goals_text
    assert "repository ready for limited runtime design work" in readme_text
    assert "runtime readiness achieved" not in readme_text
