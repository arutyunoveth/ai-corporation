from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_mvp_runtime_phase_1_final_docs_exist():
    required_docs = [
        LAUNCH_DIR / "mvp_runtime_phase_1_final_review.md",
        LAUNCH_DIR / "mvp_runtime_phase_1_exit_decision.md",
        LAUNCH_DIR / "mvp_runtime_phase_1_post_phase_recommendations.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing I1-S4 deliverable: {path.name}"


def test_mvp_runtime_phase_1_exit_decision_is_explicit_and_bounded():
    readme_text = _read(REPO_ROOT / "README.md")
    review_text = _read(LAUNCH_DIR / "mvp_runtime_phase_1_final_review.md")
    exit_text = _read(LAUNCH_DIR / "mvp_runtime_phase_1_exit_decision.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "`Continue bounded MVP runtime implementation`" in exit_text
    assert "MVP Runtime Implementation Phase 1 block completed." in readme_text
    assert "does **not** authorize broad deferred-runtime opening" in review_text
    assert "| M-049 | Agent Registry | Implemented as bounded internal registry" in mapping_text
    assert "| M-050 | Prompt / Schema Library | Implemented as bounded internal prompt/schema asset metadata" in mapping_text


def test_mvp_runtime_phase_1_current_governance_truth_is_honest():
    readme_text = _read(REPO_ROOT / "README.md")
    checklist_text = _read(LAUNCH_DIR / "Repository_Public_State_Checklist.md")
    recommendations_text = _read(LAUNCH_DIR / "mvp_runtime_phase_1_post_phase_recommendations.md")

    assert "Current governance truth: `M-049` and `M-050` are `BOUNDED_IMPLEMENTED`" in readme_text
    assert "`M-049` remains `BOUNDED_IMPLEMENTED` only" in checklist_text
    assert "`M-050` remains `BOUNDED_IMPLEMENTED` only" in checklist_text
    assert "not broad runtime opening" in recommendations_text
