from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class TestPP0Gitignore:
    def test_local_pilot_runs_ignored(self):
        gitignore = ROOT / ".gitignore"
        text = gitignore.read_text(encoding="utf-8")
        assert "/local_pilot_runs/" in text

    def test_pilot_runs_ignored(self):
        gitignore = ROOT / ".gitignore"
        text = gitignore.read_text(encoding="utf-8")
        assert "pilot_runs/" in text

    def test_tmp_partner_exports_ignored(self):
        gitignore = ROOT / ".gitignore"
        text = gitignore.read_text(encoding="utf-8")
        assert "tmp/partner_exports/" in text

    def test_gitkeep_exists(self):
        assert (ROOT / "local_pilot_runs/.gitkeep").exists()


class TestPP0TemplatesExist:
    def test_partner_profile_template_exists(self):
        assert (ROOT / "docs/product/templates/Partner_Profile_Template.md").exists()

    def test_tender_intake_template_exists(self):
        assert (ROOT / "docs/product/templates/Tender_Intake_Template.md").exists()

    def test_pilot_call_notes_template_exists(self):
        assert (ROOT / "docs/product/templates/Pilot_Call_Notes_Template.md").exists()

    def test_partner_feedback_template_exists(self):
        assert (ROOT / "docs/product/templates/Partner_Feedback_Template.md").exists()

    def test_pilot_outcome_template_exists(self):
        assert (ROOT / "docs/product/templates/Pilot_Outcome_Template.md").exists()

    def test_restricted_paid_pilot_checklist_template_exists(self):
        assert (ROOT / "docs/product/templates/Restricted_Paid_Pilot_Checklist.md").exists()


class TestPP0RunbookAndPolicy:
    def test_operations_runbook_exists(self):
        runbook = ROOT / "docs/product/Restricted_Paid_Pilot_Operations_Runbook.md"
        assert runbook.exists()
        text = runbook.read_text(encoding="utf-8")
        assert "manual-control" in text
        assert "export guard" in text

    def test_local_data_handling_policy_exists(self):
        policy = ROOT / "docs/product/Local_Pilot_Data_Handling_Policy.md"
        assert policy.exists()
        text = policy.read_text(encoding="utf-8")
        assert "must never be committed" in text
        assert "local ignored folders" in text
        assert "export/redaction guard" in text

    def test_first_pilot_checklist_exists(self):
        checklist = ROOT / "docs/product/First_Restricted_Pilot_Checklist.md"
        assert checklist.exists()
        text = checklist.read_text(encoding="utf-8")
        assert "Partner Selection" in text
        assert "Export Generation" in text
        assert "Manual Delivery" in text


class TestPP0PolicyStatements:
    def test_runbook_no_automation(self):
        text = (ROOT / "docs/product/Restricted_Paid_Pilot_Operations_Runbook.md").read_text(encoding="utf-8")
        assert "manual-control" in text

    def test_data_policy_no_real_data_committed(self):
        text = (ROOT / "docs/product/Local_Pilot_Data_Handling_Policy.md").read_text(encoding="utf-8")
        assert "must never be committed" in text

    def test_data_policy_manual_delivery_only(self):
        text = (ROOT / "docs/product/Restricted_Paid_Pilot_Operations_Runbook.md").read_text(encoding="utf-8")
        assert "external channel" in text
        assert "from the repository" in text

    def test_data_policy_no_external_automation(self):
        text = (ROOT / "docs/product/Restricted_Paid_Pilot_Operations_Runbook.md").read_text(encoding="utf-8")
        assert "Never send automated" in text
        assert "Never attempt procurement" in text


class TestPP0DocsIndex:
    def test_root_readme_references_pp0(self):
        readme = ROOT / "README.md"
        text = readme.read_text(encoding="utf-8")
        assert "Restricted Paid Pilot Operations Setup" in text or "PP0" in text

    def test_product_readme_references_pp0(self):
        readme = ROOT / "docs/product/README.md"
        text = readme.read_text(encoding="utf-8")
        assert "Restricted Paid Pilot Operations Setup" in text or "PP0" in text

    def test_backlog_references_pp0(self):
        backlog = ROOT / "docs/product/Product_Backlog.md"
        text = backlog.read_text(encoding="utf-8")
        assert "PP0" in text
