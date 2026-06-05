from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_internal_steady_state_optimization_locked_package_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Master_Plan.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_S1_Baseline_Setup.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_S2_Cycle_1.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_S3_Cycle_2_Repeatability_Check.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_S4_Review_Exit_Decision.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing optimization locked doc: {path.name}"


def test_optimization_s1_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Charter.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Baseline_Scope.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Baseline_Observation_Template.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Queue_Criteria.md",
        LAUNCH_DIR / "Internal_Steady_State_Optimization_Decision_Log_Template.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing O1-S1 deliverable: {path.name}"


def test_readme_reflects_optimization_final_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    charter_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Charter.md")
    sprint_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_S1_Baseline_Setup.md")

    assert "Internal Steady-State Optimization" in readme_text
    assert "Internal Steady-State Optimization block completed." in readme_text
    assert "Final phase decision: `Continue optimized internal usage`." in readme_text
    assert "operator-assisted" in charter_text
    assert "manual-control" in sprint_text


def test_reserved_and_deferred_slots_remain_honest_in_optimization_s1():
    readme_text = _read(REPO_ROOT / "README.md")
    master_plan_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Master_Plan.md")
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
    assert "Recommended next step: `continue optimized internal usage under the same controlled restrictions while keeping separate runtime planning as an explicit later decision`." in readme_text


def test_optimization_s1_docs_do_not_claim_runtime_opening_or_external_launch():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    charter_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Charter.md").lower()
    scope_text = _read(LAUNCH_DIR / "Internal_Steady_State_Optimization_Baseline_Scope.md").lower()

    assert "runtime reopening" in charter_text
    assert "externalization" in scope_text
    assert "continue optimized internal usage" in readme_text
    assert "pilot launched" not in readme_text
