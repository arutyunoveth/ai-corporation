from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_broader_internal_steady_state_locked_package_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Broader_Internal_Steady_State_Usage_Master_Plan.md",
        LAUNCH_DIR / "Broader_Internal_Steady_State_Usage_S1_Steady_State_Setup.md",
        LAUNCH_DIR / "Broader_Internal_Steady_State_Usage_S2_Operational_Cycle_1.md",
        LAUNCH_DIR / "Broader_Internal_Steady_State_Usage_S3_Operational_Cycle_2_Load_Cadence_Check.md",
        LAUNCH_DIR / "Broader_Internal_Steady_State_Usage_S4_Review_Exit_Decision.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing steady-state locked doc: {path.name}"


def test_steady_state_s1_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Steady_State_Usage_Charter.md",
        LAUNCH_DIR / "Steady_State_Usage_Scope_Boundaries.md",
        LAUNCH_DIR / "Steady_State_Usage_Operator_Workload_Norms.md",
        LAUNCH_DIR / "Steady_State_Usage_Cadence_Rules.md",
        LAUNCH_DIR / "Steady_State_Usage_Escalation_Rules.md",
        LAUNCH_DIR / "Steady_State_Usage_Decision_Log_Template.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S1 steady-state deliverable: {path.name}"


def test_readme_reflects_steady_state_final_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    charter_text = _read(LAUNCH_DIR / "Steady_State_Usage_Charter.md")
    sprint_text = _read(LAUNCH_DIR / "Broader_Internal_Steady_State_Usage_S1_Steady_State_Setup.md")

    assert "Broader Internal Steady-State Usage" in readme_text
    assert "Broader Internal Steady-State Usage block completed." in readme_text
    assert "Final phase decision: `Continue internal steady-state usage`." in readme_text
    assert "operator-assisted" in charter_text
    assert "manual-control" in sprint_text


def test_reserved_and_deferred_slots_remain_honest_in_steady_state_s1():
    readme_text = _read(REPO_ROOT / "README.md")
    master_plan_text = _read(LAUNCH_DIR / "Broader_Internal_Steady_State_Usage_Master_Plan.md")
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
    assert "Recommended next step: `continue internal steady-state usage under the same controlled restrictions while keeping future runtime planning explicitly separate`." in readme_text


def test_steady_state_s1_docs_do_not_claim_autonomous_or_external_launch():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    charter_text = _read(LAUNCH_DIR / "Steady_State_Usage_Charter.md").lower()
    scope_text = _read(LAUNCH_DIR / "Steady_State_Usage_Scope_Boundaries.md").lower()

    assert "autonomous" in charter_text
    assert "external commercialization" in scope_text
    assert "continue internal steady-state usage" in readme_text
    assert "pilot launched" not in readme_text
