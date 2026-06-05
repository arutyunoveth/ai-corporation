from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_deferred_runtime_planning_locked_package_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Deferred_Runtime_Planning_Master_Plan.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_S1_Scope_Constraints.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_S2_M049_M050_Readiness_Architecture.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_S3_M052_M055_Activation_Boundaries.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_S4_Decision_Roadmap.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing deferred runtime planning locked doc: {path.name}"


def test_deferred_runtime_planning_s1_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Deferred_Runtime_Planning_Charter.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_Constraints_Register.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_Non_Goals.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_Prerequisites.md",
        LAUNCH_DIR / "Deferred_Runtime_Planning_Decision_Log_Template.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing P1-S1 deliverable: {path.name}"


def test_readme_reflects_deferred_runtime_planning_phase_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    charter_text = _read(LAUNCH_DIR / "Deferred_Runtime_Planning_Charter.md")
    sprint_text = _read(LAUNCH_DIR / "Deferred_Runtime_Planning_S1_Scope_Constraints.md")

    assert "Deferred Runtime Planning" in readme_text
    assert "repository ready for deferred runtime planning architecture work" in readme_text
    assert "no runtime opening" in charter_text
    assert "без opening `M-049/M-050`" in sprint_text


def test_reserved_and_deferred_slots_remain_honest_in_deferred_runtime_planning_s1():
    readme_text = _read(REPO_ROOT / "README.md")
    master_plan_text = _read(LAUNCH_DIR / "Deferred_Runtime_Planning_Master_Plan.md")
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

    assert "opening `M-049 / M-050` in runtime" in master_plan_text
    assert "declaring `M-052..M-055` fully implemented runtime modules" in master_plan_text
    assert "repository ready for deferred runtime planning architecture work" in readme_text


def test_deferred_runtime_planning_s1_docs_do_not_claim_runtime_completion():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    charter_text = _read(LAUNCH_DIR / "Deferred_Runtime_Planning_Charter.md").lower()
    non_goals_text = _read(LAUNCH_DIR / "Deferred_Runtime_Planning_Non_Goals.md").lower()

    assert "runtime implementation" in charter_text
    assert "implementing `m-049 agent registry`" in non_goals_text
    assert "repository ready for deferred runtime planning architecture work" in readme_text
    assert "runtime readiness achieved" not in readme_text
