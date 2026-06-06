import subprocess
import sys
from pathlib import Path


class TestDP6DryRunScript:
    def test_dry_run_script_exists(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_design_partner_pilot_dry_run.py"
        assert script.exists()

    def test_dry_run_script_completes(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_design_partner_pilot_dry_run.py"
        result = subprocess.run(
            [sys.executable, str(script), "--output-dir", "/tmp/dp6_dry_run_test"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0, f"Script failed: {result.stderr}"

    def test_dry_run_creates_outputs(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_design_partner_pilot_dry_run.py"
        output_dir = Path("/tmp/dp6_dry_run_outputs")
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)

        result = subprocess.run(
            [sys.executable, str(script), "--output-dir", str(output_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert output_dir.exists()

        files = list(output_dir.iterdir())
        md_files = [f for f in files if f.suffix == ".md"]
        json_files = [f for f in files if f.suffix == ".json"]
        assert len(md_files) >= 1, f"No markdown files found in {output_dir}"
        assert len(json_files) >= 1, f"No json files found in {output_dir}"

    def test_export_guard_enforced_in_output(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_design_partner_pilot_dry_run.py"
        output_dir = Path("/tmp/dp6_dry_run_guard")
        if output_dir.exists():
            import shutil
            shutil.rmtree(output_dir)

        subprocess.run(
            [sys.executable, str(script), "--output-dir", str(output_dir)],
            capture_output=True, text=True, timeout=30,
        )

        summary_path = output_dir / "dry_run_summary.json"
        assert summary_path.exists()
        import json
        summary = json.loads(summary_path.read_text(encoding="utf-8"))

        assert summary["restricted_sensitive_blocked"] is True
        assert summary["internal_only_redacted"] is True
        assert summary["operator_visible_redacted"] is True
        assert summary["customer_report_included"] is True

    def test_no_network_or_db_in_output(self):
        script = Path(__file__).resolve().parents[1] / "scripts" / "run_design_partner_pilot_dry_run.py"
        code = script.read_text(encoding="utf-8")
        assert "import sqlalchemy" not in code
        assert "SessionLocal" not in code
        assert "requests." not in code
        assert "smtplib" not in code
        assert "sendmail" not in code.lower()


class TestDP6Docs:
    def test_sample_result_exists(self):
        path = Path(__file__).resolve().parents[1] / "docs" / "product" / "samples" / "Design_Partner_Dry_Run_Sample_Result.md"
        assert path.exists()

    def test_dry_run_template_exists(self):
        path = Path(__file__).resolve().parents[1] / "docs" / "product" / "Design_Partner_Dry_Run_Result_Template.md"
        assert path.exists()

    def test_dp6_sprint_spec_exists(self):
        path = Path(__file__).resolve().parents[1] / "docs" / "product" / "DP6_Design_Partner_Dry_Run.md"
        assert path.exists()
