from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_m052_m055_activation_boundary_docs_exist():
    required_docs = [
        LAUNCH_DIR / "M052_M055_Activation_Boundaries.md",
        LAUNCH_DIR / "M052_M055_Activation_Matrix.md",
        LAUNCH_DIR / "M052_M055_Compensating_Controls_Mapping.md",
        LAUNCH_DIR / "M052_M055_Readiness_Triggers.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing P1-S3 deliverable: {path.name}"


def test_readme_and_docs_state_m052_m055_boundaries_but_not_activation():
    readme_text = _read(REPO_ROOT / "README.md")
    boundaries_text = _read(LAUNCH_DIR / "M052_M055_Activation_Boundaries.md")
    triggers_text = _read(LAUNCH_DIR / "M052_M055_Readiness_Triggers.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "M-052..M-055 activation boundaries are now formally documented." in readme_text
    assert "Deferred Runtime Planning block completed." in readme_text
    assert "remain deferred" in boundaries_text
    assert "not activation" in triggers_text.lower()
    assert "| M-052 | Notification Layer |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text
