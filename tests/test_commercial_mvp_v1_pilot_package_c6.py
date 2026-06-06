from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PRODUCT = ROOT / "docs" / "product"


def test_c6_pilot_package_docs_exist():
    required = [
        PRODUCT / "Pilot_Playbook_MVP_v1.md",
        PRODUCT / "Customer_Onboarding_MVP_v1.md",
        PRODUCT / "Operator_Runbook_MVP_v1.md",
        PRODUCT / "Pricing_Hypotheses.md",
        PRODUCT / "Pilot_Success_Metrics.md",
        PRODUCT / "Known_Limitations_MVP_v1.md",
        PRODUCT / "MVP_v1_Final_Audit.md",
        PRODUCT / "Post_MVP_v1_Roadmap_Revision_Proposal.md",
        PRODUCT / "samples" / "Commercial_MVP_v1_Sample_Customer_Report.md",
    ]
    missing = [str(path.relative_to(ROOT)) for path in required if not path.exists()]
    assert not missing


def test_c6_final_audit_has_explicit_go_with_restrictions():
    audit = (PRODUCT / "MVP_v1_Final_Audit.md").read_text(encoding="utf-8")
    assert "GO with restrictions" in audit
    assert "no autonomous bid submission" in audit
    assert "no procurement platform integration" in audit


def test_c6_runbook_and_limitations_preserve_non_goals():
    runbook = (PRODUCT / "Operator_Runbook_MVP_v1.md").read_text(encoding="utf-8")
    limitations = (PRODUCT / "Known_Limitations_MVP_v1.md").read_text(encoding="utf-8")
    assert "scripts/run_commercial_mvp_v1_demo.py" in runbook
    assert "final submission remains manual" in runbook
    assert "no automatic supplier email delivery" in limitations
    assert "no EDS/signature flow" in limitations
