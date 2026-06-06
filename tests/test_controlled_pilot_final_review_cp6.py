from pathlib import Path


PRODUCT_DIR = Path("docs/product")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_controlled_pilot_final_review_docs_exist_and_match_decision():
    audit = _read(PRODUCT_DIR / "Controlled_Pilot_Final_Audit.md")
    decision = _read(PRODUCT_DIR / "Controlled_Pilot_GO_NO_GO_Decision.md")
    roadmap = _read(PRODUCT_DIR / "Post_Pilot_Roadmap_Revision.md")
    readme = _read(PRODUCT_DIR / "README.md")
    root_readme = _read(Path("README.md"))

    assert "GO to unpaid/discounted design-partner pilot" in audit
    assert "GO to unpaid/discounted design-partner pilot" in decision
    assert "design-partner pilot stabilization" in roadmap
    assert "Controlled Commercial Pilot Stage review is complete" in readme
    assert "Current product recommendation: `GO to restricted paid pilot with manual-control boundaries`." in root_readme


def test_controlled_pilot_final_review_keeps_non_goals_closed():
    decision = _read(PRODUCT_DIR / "Controlled_Pilot_GO_NO_GO_Decision.md")
    roadmap = _read(PRODUCT_DIR / "Post_Pilot_Roadmap_Revision.md")

    assert "autonomous bid submission" in decision
    assert "procurement platform integration" in roadmap
    assert "supplier outreach automation" in roadmap
    assert "broad autonomous runtime" in roadmap
