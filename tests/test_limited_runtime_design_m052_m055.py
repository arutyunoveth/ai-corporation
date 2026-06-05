from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_m052_m055_supporting_runtime_design_docs_exist():
    required_docs = [
        LAUNCH_DIR / "M052_M055_Supporting_Runtime_Design.md",
        LAUNCH_DIR / "M052_M055_Dependency_Matrix.md",
        LAUNCH_DIR / "M052_M055_Coordination_Model.md",
        LAUNCH_DIR / "M052_M055_Implementation_Gate_Conditions.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing D1-S3 deliverable: {path.name}"


def test_readme_and_docs_state_m052_m055_supporting_design_but_not_runtime():
    readme_text = _read(REPO_ROOT / "README.md")
    design_text = _read(LAUNCH_DIR / "M052_M055_Supporting_Runtime_Design.md")
    gate_text = _read(LAUNCH_DIR / "M052_M055_Implementation_Gate_Conditions.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "M-052..M-055 supporting runtime design is now formally documented." in readme_text
    assert "not activated by this design package" in design_text
    assert "not activation" in gate_text.lower()
    assert "| M-052 | Notification Layer |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text
