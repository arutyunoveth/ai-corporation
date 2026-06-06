from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_limited_runtime_implementation_gate_locked_package_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Master_Plan.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_S1_Scope_Safety_Lock.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_S2_MVP_Runtime_Slice_Definition.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_S3_Readiness_Delivery_Plan.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_S4_Gate_Review_MVP_GoNoGo.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing limited runtime implementation gate locked doc: {path.name}"


def test_limited_runtime_implementation_gate_s1_deliverables_exist():
    required_docs = [
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Charter.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Safety_Lock.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Blocked_Areas.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Decision_Log_Template.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing G1-S1 deliverable: {path.name}"


def test_readme_reflects_implementation_gate_s1_gate():
    readme_text = _read(REPO_ROOT / "README.md")
    charter_text = _read(LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Charter.md")
    sprint_text = _read(LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_S1_Scope_Safety_Lock.md")

    assert "Limited Runtime Implementation Gate" in readme_text
    assert "Limited Runtime Implementation Gate is now formally staged under a locked master plan and S1 scope/safety lock package." in readme_text
    assert "Current phase status: `repository ready for MVP runtime slice definition`." in readme_text
    assert "no implementation yet" in charter_text
    assert "без runtime implementation в этой фазе" in sprint_text


def test_reserved_and_deferred_slots_remain_honest_in_implementation_gate_s1():
    readme_text = _read(REPO_ROOT / "README.md")
    master_plan_text = _read(LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Master_Plan.md")
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

    assert "broad runtime implementation" in master_plan_text
    assert "opening all deferred slots at once" in master_plan_text
    assert "Current phase status: `repository ready for MVP runtime slice definition`." in readme_text


def test_implementation_gate_s1_docs_do_not_claim_runtime_completion():
    readme_text = _read(REPO_ROOT / "README.md").lower()
    charter_text = _read(LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Charter.md").lower()
    lock_text = _read(LAUNCH_DIR / "Limited_Runtime_Implementation_Safety_Lock.md").lower()

    assert "no implementation yet" in charter_text
    assert "do not implement runtime during this phase" in lock_text
    assert "repository ready for mvp runtime slice definition" in readme_text
    assert "mvp already implemented" not in readme_text
