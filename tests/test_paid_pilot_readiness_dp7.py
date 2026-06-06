from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestDP7DocsExist:
    def test_dp7_sprint_spec_exists(self):
        assert (ROOT / "docs/product/DP7_Paid_Pilot_Readiness_Review.md").exists()

    def test_go_no_go_decision_exists(self):
        decision = ROOT / "docs/product/Paid_Pilot_GO_NO_GO_Decision.md"
        assert decision.exists()
        text = decision.read_text(encoding="utf-8")
        assert "GO" in text or "NO-GO" in text

    def test_roadmap_revision_exists(self):
        assert (ROOT / "docs/product/Post_Design_Partner_Roadmap_Revision.md").exists()

    def test_readme_references_current_stage(self):
        readme = ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert "Design-Partner Pilot Stage is complete" in text
        assert "restricted paid pilot" in text

    def test_product_readme_references_current_stage(self):
        readme = ROOT / "docs/product/README.md"
        text = readme.read_text(encoding="utf-8")
        assert "Design-Partner Pilot Stage is complete" in text
        assert "GO to restricted paid pilot" in text

    def test_non_goals_remain_stated(self):
        decision = ROOT / "docs/product/Paid_Pilot_GO_NO_GO_Decision.md"
        text = decision.read_text(encoding="utf-8")
        assert "autonomous bid submission" in text
        assert "EDS/signature" in text
        assert "procurement platform" in text
        assert "Supplier outreach" in text
        assert "Production SaaS" in text

    def test_dp0_dp6_artifacts_still_present(self):
        assert (ROOT / "docs/product/DP0_Publication_Audit.md").exists()
        assert (ROOT / "docs/product/DP1_Minimal_Access_Boundary.md").exists()
        assert (ROOT / "docs/product/DP2_Partner_Workspace_and_Data_Intake.md").exists()
        assert (ROOT / "docs/product/DP3_Real_Tender_Runbook_and_Redaction.md").exists()
        assert (ROOT / "docs/product/DP4_Report_Export_and_Partner_Delivery.md").exists()
        assert (ROOT / "docs/product/DP5_Feedback_and_Outcome_Loop.md").exists()
        assert (ROOT / "docs/product/DP6_Design_Partner_Dry_Run.md").exists()

    def test_dp_modules_still_present(self):
        assert (ROOT / "src/modules/pilot_access_boundary/__init__.py").exists()
        assert (ROOT / "src/modules/partner_workspace/__init__.py").exists()
        assert (ROOT / "src/modules/partner_export/__init__.py").exists()
        assert (ROOT / "src/modules/pilot_feedback/__init__.py").exists()

    def test_dp_tests_still_pass_structure(self):
        assert (ROOT / "tests/test_pilot_access_boundary_dp1.py").exists()
        assert (ROOT / "tests/test_partner_workspace_dp2.py").exists()
        assert (ROOT / "tests/test_redaction_workflow_dp3.py").exists()
        assert (ROOT / "tests/test_partner_export_dp4.py").exists()
        assert (ROOT / "tests/test_pilot_feedback_dp5.py").exists()
        assert (ROOT / "tests/test_design_partner_dry_run_dp6.py").exists()
