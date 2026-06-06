from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = REPO_ROOT / "docs" / "product"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_c1_product_docs_exist():
    required_docs = [
        PRODUCT_DIR / "README.md",
        PRODUCT_DIR / "Product_Master_Plan_v2.md",
        PRODUCT_DIR / "Commercial_MVP_v1_Roadmap.md",
        PRODUCT_DIR / "MVP_v1_Scope.md",
        PRODUCT_DIR / "MVP_v1_Non_Goals.md",
        PRODUCT_DIR / "Human_Control_Policy_v2.md",
        PRODUCT_DIR / "Product_Backlog.md",
        PRODUCT_DIR / "Repository_Public_Readiness_Check.md",
        REPO_ROOT / ".env.example",
    ]
    for path in required_docs:
        assert path.exists(), f"Missing C1 product deliverable: {path.name}"


def test_c1_readme_uses_public_repo_relative_links_and_current_status():
    readme_text = _read(REPO_ROOT / "README.md")

    assert "/Users/master/Documents/AI-Corporation" not in readme_text
    assert "Runtime Metadata Phase `I1` is complete" in readme_text
    assert "Controlled Commercial Pilot Stage is complete at the repository package level." in readme_text
    assert "Current product recommendation: `GO to restricted paid pilot with manual-control boundaries`." in readme_text
    assert "[docs/product/README.md](docs/product/README.md)" in readme_text
    assert "No broad autonomy is open." in readme_text
    assert "No external execution is open." in readme_text


def test_c1_product_docs_preserve_non_goals_and_human_control():
    scope_text = _read(PRODUCT_DIR / "MVP_v1_Scope.md")
    non_goals_text = _read(PRODUCT_DIR / "MVP_v1_Non_Goals.md")
    policy_text = _read(PRODUCT_DIR / "Human_Control_Policy_v2.md")
    readiness_text = _read(PRODUCT_DIR / "Repository_Public_Readiness_Check.md")

    assert "operator review" in scope_text.lower()
    assert "autonomous bid submission" in non_goals_text
    assert "no automatic external execution" in policy_text
    assert "M-052..M-055" in readiness_text
