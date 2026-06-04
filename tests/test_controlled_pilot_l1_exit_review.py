from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
LAUNCH_DIR = REPO_ROOT / "docs" / "10_launch"
GOVERNANCE_DIR = REPO_ROOT / "docs" / "99_governance"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_controlled_pilot_l1_final_docs_exist():
    required_docs = [
        LAUNCH_DIR / "Controlled_Pilot_L1_Final_Review.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Exit_Decision.md",
        LAUNCH_DIR / "Controlled_Pilot_L1_Post_Pilot_Recommendations.md",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing S4 deliverable: {path.name}"


def test_controlled_pilot_l1_final_decision_is_explicit_and_honest():
    readme_text = _read(REPO_ROOT / "README.md")
    exit_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Exit_Decision.md")
    final_review_text = _read(LAUNCH_DIR / "Controlled_Pilot_L1_Final_Review.md")
    mapping_text = _read(GOVERNANCE_DIR / "canonical_vs_implemented_mapping.md")

    assert "`GO with restrictions`" in exit_text
    assert "Controlled Pilot L1 block completed" in readme_text
    assert "broader internal usage under the same controlled restrictions" in exit_text
    assert "M-049" in final_review_text
    assert "M-050" in final_review_text
    assert "| M-052 | Notification Layer |" in mapping_text
    assert "| M-055 | SaaS Productization Tracker |" in mapping_text
