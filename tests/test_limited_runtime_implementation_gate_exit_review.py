from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_limited_runtime_implementation_gate_final_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Final_Review.md",
        LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Exit_Decision.md",
        LAUNCH_DIR / "MVP_Runtime_Implementation_Phase_1_Roadmap.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing G1-S4 deliverable: {path.name}"


def test_limited_runtime_implementation_gate_final_decision_is_explicit_and_bounded():
    readme_text = _read(REPO_ROOT / "README.md")
    exit_text = _read(LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Exit_Decision.md")
    review_text = _read(LAUNCH_DIR / "Limited_Runtime_Implementation_Gate_Final_Review.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "`GO to MVP runtime implementation`" in exit_text
    assert "Limited Runtime Implementation Gate block completed." in readme_text
    assert "does **not** authorize" in exit_text
    assert "not ready for broad deferred-runtime opening" in review_text
    assert "| M-049 | Agent Registry |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text
