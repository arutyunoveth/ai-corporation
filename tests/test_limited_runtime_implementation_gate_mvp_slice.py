from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mvp_runtime_slice_docs_exist():
    required_docs = [
        LAUNCH_DIR / "MVP_Runtime_Slice_Definition.md",
        LAUNCH_DIR / "MVP_Runtime_Slice_In_Scope_Out_of_Scope_Matrix.md",
        LAUNCH_DIR / "MVP_First_Implementation_Target.md",
        LAUNCH_DIR / "MVP_Deferred_Remainder_Note.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing G1-S2 deliverable: {path.name}"


def test_mvp_slice_is_explicitly_narrow_and_non_broad():
    readme_text = _read(REPO_ROOT / "README.md")
    slice_text = _read(LAUNCH_DIR / "MVP_Runtime_Slice_Definition.md")
    matrix_text = _read(LAUNCH_DIR / "MVP_Runtime_Slice_In_Scope_Out_of_Scope_Matrix.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "First MVP runtime slice is now formally defined." in readme_text
    assert "bounded internal metadata-control slice for M-049/M-050" in slice_text
    assert "agent execution runtime | `OUT_OF_SCOPE`" in matrix_text
    assert "M-052 Notification Layer" in matrix_text
    assert "| M-049 | Agent Registry |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text
