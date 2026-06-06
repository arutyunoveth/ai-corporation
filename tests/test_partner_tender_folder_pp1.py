import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "local_pilot_runs" / "partner_001"
TENDER_DIR = FIXTURE_DIR / "tender_001"

SCRIPT = ROOT / "scripts" / "run_partner_tender_folder.py"


def _run_script(output_dir: Path) -> subprocess.CompletedProcess:
    """Run the PP1 script with the synthetic fixture and a specific output dir."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT),
         "--partner-id", "partner_001",
         "--tender-dir", str(TENDER_DIR),
         "--provider", "stub",
         "--output-dir", str(output_dir / "04_system_output")],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return result


@pytest.fixture(scope="module")
def script_output(tmp_path_factory):
    """Run the script once per module into a unique temp dir."""
    out = tmp_path_factory.mktemp("pp1_output")
    result = _run_script(out)
    assert result.returncode == 0, f"Script failed:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    return out


# ---------------------------------------------------------------------------
# Script existence and structural checks
# ---------------------------------------------------------------------------

class TestPP1ScriptStructure:
    def test_script_exists(self):
        assert SCRIPT.exists()

    def test_script_accepts_provider_args(self):
        code = SCRIPT.read_text(encoding="utf-8")
        assert '--provider' in code
        assert "'stub'" in code or '"stub"' in code
        assert "'llm'" in code or '"llm"' in code

    def test_script_has_required_args(self):
        code = SCRIPT.read_text(encoding="utf-8")
        assert "partner-id" in code
        assert "tender-dir" in code
        assert "output-dir" in code or "output_dir" in code


# ---------------------------------------------------------------------------
# Successful execution and output content
# ---------------------------------------------------------------------------

class TestPP1SuccessfulRun:
    def test_run_succeeds(self, script_output):
        assert (script_output / "04_system_output").is_dir()

    def test_all_output_files_created(self, script_output):
        sys_out = script_output / "04_system_output"
        export_out = TENDER_DIR / "05_partner_export"
        expected = [
            sys_out / "run_summary.json",
            sys_out / "internal_analysis.md",
            export_out / "partner_report.md",
            export_out / "export_summary.json",
        ]
        for path in expected:
            assert path.exists(), f"Missing: {path}"

    def test_run_summary_has_metadata(self, script_output):
        summary = json.loads((script_output / "04_system_output" / "run_summary.json").read_text())
        assert summary["partner_id"] == "partner_001"
        assert "workspace_id" in summary and summary["workspace_id"]
        assert "export_package_id" in summary and summary["export_package_id"]
        assert "completed_at_utc" in summary

    def test_internal_analysis_has_sections(self, script_output):
        md = (script_output / "04_system_output" / "internal_analysis.md").read_text()
        assert "Internal Analysis Report" in md
        assert "Technical Requirements" in md
        assert "Preliminary Recommendation" in md

    def test_partner_report_has_content(self, script_output):
        md = (TENDER_DIR / "05_partner_export" / "partner_report.md").read_text()
        assert "Export Package" in md
        assert "partner_workspace_id" in md or "workspace ID" in md

    def test_export_summary_has_structure(self, script_output):
        export = json.loads((TENDER_DIR / "05_partner_export" / "export_summary.json").read_text())
        assert "included_sections" in export
        assert "redacted_sections" in export
        assert "blocked_sections" in export

    def test_three_intake_records_created(self, script_output):
        summary = json.loads((script_output / "04_system_output" / "run_summary.json").read_text())
        assert len(summary["intake_records"]) == 3


# ---------------------------------------------------------------------------
# Missing / invalid folder structure
# ---------------------------------------------------------------------------

class TestPP1MissingFolder:
    def test_missing_tender_dir_fails(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--partner-id", "test",
             "--tender-dir", "/tmp/pp1_dir_does_not_exist_xyz",
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "does not exist" in result.stdout + result.stderr

    def test_missing_extracted_text_files_fails(self):
        temp = Path("/tmp/pp1_missing_extracted")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        (temp / "01_raw_docs").mkdir()
        (temp / "02_extracted_text").mkdir()
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--partner-id", "test",
             "--tender-dir", str(temp),
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "Missing required extracted text" in result.stdout + result.stderr

    def test_missing_extracted_dir_fails(self):
        temp = Path("/tmp/pp1_no_extracted_dir")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--partner-id", "test",
             "--tender-dir", str(temp),
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "02_extracted_text" in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Export guard verification
# ---------------------------------------------------------------------------

class TestPP1ExportGuard:
    def test_restricted_sections_blocked(self):
        export = json.loads((TENDER_DIR / "05_partner_export" / "export_summary.json").read_text())
        assert "sensitive_legal_note" in export.get("blocked_sections", [])

    def test_internal_trace_redacted(self):
        export = json.loads((TENDER_DIR / "05_partner_export" / "export_summary.json").read_text())
        assert "runtime_trace" in export.get("redacted_sections", [])

    def test_operator_decision_redacted(self):
        export = json.loads((TENDER_DIR / "05_partner_export" / "export_summary.json").read_text())
        assert "operator_decision" in export.get("redacted_sections", [])

    def test_customer_report_included(self):
        export = json.loads((TENDER_DIR / "05_partner_export" / "export_summary.json").read_text())
        assert "customer_report" in export.get("included_sections", [])

    def test_blocked_in_run_summary(self):
        summary = json.loads((TENDER_DIR / "05_partner_export" / "export_summary.json").read_text())
        blocked = summary.get("blocked_sections", [])
        assert any("sensitive" in b.lower() for b in blocked)


# ---------------------------------------------------------------------------
# No external actions — script source analysis
# ---------------------------------------------------------------------------

class TestPP1NoExternalActions:
    def test_no_sqlalchemy_top_import(self):
        code = SCRIPT.read_text()
        # The PP1 script does NOT import sqlalchemy at the top level
        assert "from sqlalchemy" not in code or "_try_llm_analysis" in code

    def test_no_smtplib(self):
        code = SCRIPT.read_text()
        assert "smtplib" not in code
        assert "sendmail" not in code.lower()

    def test_no_requests(self):
        code = SCRIPT.read_text()
        assert "requests." not in code

    def test_no_subprocess_in_script(self):
        code = SCRIPT.read_text()
        assert "subprocess" not in code

    def test_no_urllib(self):
        code = SCRIPT.read_text()
        assert "urllib" not in code


# ---------------------------------------------------------------------------
# Synthetic fixture — no real data
# ---------------------------------------------------------------------------

class TestPP1SyntheticFixture:
    def test_extracted_text_is_synthetic(self):
        for name in ["notice.txt", "technical_spec.txt", "contract_draft.txt"]:
            text = (TENDER_DIR / "02_extracted_text" / name).read_text()
            assert "synthetic" in text.lower() or "test" in text.lower(), \
                f"Fixture {name} appears to contain real data"

    def test_partner_profile_is_synthetic(self):
        text = (FIXTURE_DIR / "partner_profile.md").read_text()
        assert "synthetic" in text.lower(), "Partner profile appears to contain real data"


# ---------------------------------------------------------------------------
# PR1 docs
# ---------------------------------------------------------------------------

class TestPP1Docs:
    def test_runbook_exists(self):
        assert (ROOT / "docs/product/Run_Partner_Tender_Folder.md").exists()

    def test_folder_template_exists(self):
        assert (ROOT / "docs/product/templates/local_pilot_folder_template.md").exists()

    def test_runbook_mentions_no_auto(self):
        text = (ROOT / "docs/product/Run_Partner_Tender_Folder.md").read_text()
        assert "Never commit" in text or "No automated" in text

    def test_folder_template_has_structure_refs(self):
        text = (ROOT / "docs/product/templates/local_pilot_folder_template.md").read_text()
        assert "02_extracted_text" in text
        assert "05_partner_export" in text
