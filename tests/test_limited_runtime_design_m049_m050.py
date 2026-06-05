from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_m049_m050_limited_runtime_design_docs_exist():
    required_docs = [
        LAUNCH_DIR / "M049_M050_Limited_Runtime_Design.md",
        LAUNCH_DIR / "M049_M050_Contracts_and_Interfaces_Draft.md",
        LAUNCH_DIR / "M049_M050_Activation_Sequencing.md",
        LAUNCH_DIR / "M049_M050_Safety_and_Risk_Note.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing D1-S2 deliverable: {path.name}"


def test_readme_and_docs_state_m049_m050_are_designed_but_not_opened():
    readme_text = _read(REPO_ROOT / "README.md")
    design_text = _read(LAUNCH_DIR / "M049_M050_Limited_Runtime_Design.md")
    sequencing_text = _read(LAUNCH_DIR / "M049_M050_Activation_Sequencing.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "M-049/M-050 limited runtime design is now formally documented." in readme_text
    assert "does **not** authorize runtime implementation" in design_text
    assert "not as an authorization to activate runtime now" in sequencing_text
    assert "| M-049 | Agent Registry |" in mapping_text
    assert "| M-050 | Prompt / Schema Library |" in mapping_text
