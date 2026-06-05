from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_m049_m050_readiness_docs_exist():
    required_docs = [
        LAUNCH_DIR / "M049_M050_Readiness_Architecture.md",
        LAUNCH_DIR / "M049_M050_Dependency_Map.md",
        LAUNCH_DIR / "M049_M050_Risk_Register.md",
        LAUNCH_DIR / "M049_M050_Phasing_Draft.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing P1-S2 deliverable: {path.name}"


def test_readme_and_docs_state_m049_m050_are_documented_but_not_opened():
    readme_text = _read(REPO_ROOT / "README.md")
    architecture_text = _read(LAUNCH_DIR / "M049_M050_Readiness_Architecture.md")
    phasing_text = _read(LAUNCH_DIR / "M049_M050_Phasing_Draft.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "M-049/M-050 readiness architecture is now formally documented." in readme_text
    assert "Current phase gate: `M-049/M-050 readiness architecture documented`." in readme_text
    assert "does **not** authorize runtime implementation" in architecture_text
    assert "immediate runtime implementation of `M-049/M-050`" in phasing_text
    assert "| M-049 | Agent Registry |" in mapping_text
    assert "| M-050 | Prompt / Schema Library |" in mapping_text
