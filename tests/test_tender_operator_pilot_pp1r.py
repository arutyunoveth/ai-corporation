import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from scripts.run_tender_operator_pilot import _resolve_provider_request

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_DIR = ROOT / "tests" / "fixtures" / "local_pilot_runs" / "tender_operator_001"
TENDER_DIR = FIXTURE_DIR / "tender_001"

SCRIPT = ROOT / "scripts" / "run_tender_operator_pilot.py"
OLD_PP1_SCRIPT = ROOT / "scripts" / "run_partner_tender_folder.py"


def _run_script(
    output_dir: Path,
    tender_dir: Path = TENDER_DIR,
    operator_id: str = "tender_operator_001",
    provider: str = "stub",
    extra_env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run the PP1R script with given params."""
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(SCRIPT),
         "--operator-id", operator_id,
         "--tender-dir", str(tender_dir),
         "--provider", provider,
         "--output-dir", str(output_dir)],
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def tkp_output(tmp_path_factory):
    """Run PP1R with TKP files present (the default fixture has TKP)."""
    out = tmp_path_factory.mktemp("pp1r_tkp")
    result = _run_script(out)
    assert result.returncode == 0, f"TKP script failed:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    return out, TENDER_DIR


@pytest.fixture(scope="module")
def no_tkp_output(tmp_path_factory):
    """Run PP1R with no TKP files (copy fixture and remove 04_tkp)."""
    src = TENDER_DIR
    tmp = Path(tmp_path_factory.mktemp("pp1r_no_tkp"))
    dst = tmp / src.name
    shutil.copytree(src, dst)
    # Remove TKP dir
    tkp_dir = dst / "04_tkp"
    if tkp_dir.exists():
        shutil.rmtree(tkp_dir)
    out = tmp / "output"
    result = _run_script(out, tender_dir=dst)
    assert result.returncode == 0, f"No-TKP script failed:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
    return out, dst


def _sys_output(output_info):
    return output_info[0]


def _tender_dir(output_info):
    return output_info[1]


# ---------------------------------------------------------------------------
# Script existence and structure
# ---------------------------------------------------------------------------

class TestPP1RScriptStructure:
    def test_script_exists(self):
        assert SCRIPT.exists()

    def test_old_pp1_script_still_exists(self):
        assert OLD_PP1_SCRIPT.exists()

    def test_script_has_tender_operator_args(self):
        code = SCRIPT.read_text()
        assert "operator-id" in code
        assert "tender-dir" in code
        assert "output-dir" in code
        assert "provider" in code

    def test_script_supports_stub_and_llm(self):
        code = SCRIPT.read_text()
        assert "'stub'" in code or '"stub"' in code
        assert "'llm'" in code or '"llm"' in code

    def test_provider_resolution_rules(self):
        assert _resolve_provider_request("stub", "gigachat") == ("stub", "stub")
        assert _resolve_provider_request("llm", "stub") == ("stub", "stub")
        assert _resolve_provider_request("llm", "gigachat") == ("llm", "gigachat")
        assert _resolve_provider_request("openai_compatible", "stub") == ("llm", "openai_compatible")
        assert _resolve_provider_request("gigachat", "stub") == ("llm", "gigachat")
        assert _resolve_provider_request("yandex", "stub") == ("llm", "yandex")
        assert _resolve_provider_request("alice", "stub") == ("llm", "alice")
        assert _resolve_provider_request("cloudru", "stub") == ("llm", "cloudru")


# ---------------------------------------------------------------------------
# Successful run — no TKP
# ---------------------------------------------------------------------------

class TestPP1RNoTKP:
    def test_run_succeeds_no_tkp(self, no_tkp_output):
        out, _ = no_tkp_output
        assert (out).is_dir()

    def test_no_tkp_required_outputs_exist(self, no_tkp_output):
        out, _ = no_tkp_output
        expected = [
            out / "run_summary.json",
            out / "internal_operator_analysis.md",
            out / "requirements.json",
            out / "supplier_questions.json",
            out / "rfq_request_draft.md",
            out / "calibrated_contract_risk_memo.md",
        ]
        for p in expected:
            assert p.exists(), f"Missing no-TKP output: {p}"

    def test_no_tkp_optional_outputs_absent(self, no_tkp_output):
        out, _ = no_tkp_output
        optional = [
            out / "tkp_normalized_quotes.json",
            out / "tkp_normalization_report.md",
            out / "tkp_comparison.json",
            out / "economics_summary.json",
            out / "bid_decision_recommendation.md",
        ]
        for p in optional:
            assert not p.exists(), f"TKP output should not exist: {p}"

    def test_no_tkp_status_is_rfq_ready(self, no_tkp_output):
        out, _ = no_tkp_output
        summary = json.loads((out / "run_summary.json").read_text())
        assert "rfq_ready" in summary.get("pilot_status", "")

    def test_no_tkp_tkp_found_false(self, no_tkp_output):
        out, _ = no_tkp_output
        summary = json.loads((out / "run_summary.json").read_text())
        assert summary.get("tkp_found") is False

    def test_no_tkp_has_requirements_and_questions(self, no_tkp_output):
        out, _ = no_tkp_output
        reqs = json.loads((out / "requirements.json").read_text())
        assert len(reqs.get("technical_requirements", [])) > 0

        questions = json.loads((out / "supplier_questions.json").read_text())
        assert len(questions) > 0


# ---------------------------------------------------------------------------
# Successful run — with TKP
# ---------------------------------------------------------------------------

class TestPP1RWithTKP:
    def test_run_succeeds_with_tkp(self, tkp_output):
        out, _ = tkp_output
        assert out.is_dir()

    def test_with_tkp_all_outputs_exist(self, tkp_output):
        out, tender = tkp_output
        expected = [
            out / "run_summary.json",
            out / "internal_operator_analysis.md",
            out / "requirements.json",
            out / "supplier_questions.json",
            out / "rfq_request_draft.md",
            out / "calibrated_contract_risk_memo.md",
            out / "tkp_normalized_quotes.json",
            out / "tkp_normalization_report.md",
            out / "tkp_comparison.json",
            out / "economics_summary.json",
            out / "bid_decision_recommendation.md",
            tender / "06_partner_export" / "operator_report.md",
            tender / "06_partner_export" / "export_summary.json",
        ]
        for p in expected:
            assert p.exists(), f"Missing TKP output: {p}"

    def test_with_tkp_status_is_economics_ready(self, tkp_output):
        out, _ = tkp_output
        summary = json.loads((out / "run_summary.json").read_text())
        assert "tkp_received" in summary.get("pilot_status", "")

    def test_with_tkp_found_true(self, tkp_output):
        out, _ = tkp_output
        summary = json.loads((out / "run_summary.json").read_text())
        assert summary.get("tkp_found") is True

    def test_run_summary_has_metadata(self, tkp_output):
        out, _ = tkp_output
        summary = json.loads((out / "run_summary.json").read_text())
        assert summary["operator_id"] == "tender_operator_001"
        assert "workspace_id" in summary and summary["workspace_id"]
        assert "export_package_id" in summary and summary["export_package_id"]
        assert "completed_at_utc" in summary
        assert "supplier_sourcing" in summary
        assert summary["supplier_sourcing"]["manual_candidates_file_found"] is True

    def test_internal_analysis_contains_supplier_sourcing(self, tkp_output):
        out, _ = tkp_output
        analysis = (out / "internal_operator_analysis.md").read_text()
        assert "## Supplier Sourcing" in analysis
        assert "supplier_candidates.md" in analysis

    def test_three_intake_records(self, tkp_output):
        out, _ = tkp_output
        summary = json.loads((out / "run_summary.json").read_text())
        assert len(summary["intake_records"]) == 3

    def test_tkp_comparison_has_suppliers(self, tkp_output):
        out, _ = tkp_output
        comp = json.loads((out / "tkp_comparison.json").read_text())
        assert len(comp.get("suppliers", [])) >= 2
        assert comp["method"] in {"deterministic_normalized", "llm_normalized"}

    def test_tkp_normalized_quotes_exist(self, tkp_output):
        out, _ = tkp_output
        quotes = json.loads((out / "tkp_normalized_quotes.json").read_text())
        assert len(quotes) >= 2
        assert all("normalization_status" in quote for quote in quotes)
        assert all("extraction_confidence" in quote for quote in quotes)

    def test_bid_decision_has_recommendation(self, tkp_output):
        out, _ = tkp_output
        bd = json.loads((out / "tkp_comparison.json").read_text())
        assert bd is not None

    def test_llm_mode_uses_controlled_workflow_artifacts(self, tmp_path):
        out = tmp_path / "llm_output"
        db_path = tmp_path / "llm_workflow.sqlite"
        result = _run_script(
            out,
            provider="llm",
            extra_env={
                "AI_CORP_DATABASE_URL": f"sqlite:///{db_path}",
                "AI_CORP_LLM_PROVIDER": "stub",
                "AI_CORP_LLM_MODEL": "stub-controlled-model",
            },
        )
        assert result.returncode == 0, f"LLM-mode script failed:\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"

        summary = json.loads((out / "run_summary.json").read_text())
        requirements = json.loads((out / "requirements.json").read_text())
        rfq = (out / "rfq_request_draft.md").read_text()
        comparison = json.loads((out / "tkp_comparison.json").read_text())

        assert summary["analysis_mode"] == "llm_tender_operator_stub"
        assert summary["requested_provider"] == "llm"
        assert summary["resolved_provider"] == "stub"
        assert "llm_control" in requirements
        assert "llm_analysis" not in requirements
        assert requirements["llm_control"]["analysis_mode"] == "llm_tender_operator_stub"
        assert requirements["llm_control"]["resolved_provider"] == "stub"
        assert "## Requirements Summary" in rfq
        assert comparison["method"] == "llm_normalized"


# ---------------------------------------------------------------------------
# Missing folder validation
# ---------------------------------------------------------------------------

class TestPP1RMissingFolder:
    def test_missing_tender_dir_fails(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--operator-id", "test",
             "--tender-dir", "/tmp/pp1r_dir_does_not_exist_xyz",
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "does not exist" in result.stdout + result.stderr

    def test_missing_notice_txt_fails(self):
        temp = Path("/tmp/pp1r_missing_notice")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        (temp / "01_raw_docs").mkdir()
        extracted = temp / "02_extracted_text"
        extracted.mkdir()
        (extracted / "technical_spec.txt").write_text("test")
        (extracted / "contract_draft.txt").write_text("test")
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--operator-id", "test",
             "--tender-dir", str(temp),
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "notice.txt" in result.stdout + result.stderr

    def test_missing_technical_spec_txt_fails(self):
        temp = Path("/tmp/pp1r_missing_techspec")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        (temp / "01_raw_docs").mkdir()
        extracted = temp / "02_extracted_text"
        extracted.mkdir()
        (extracted / "notice.txt").write_text("test")
        (extracted / "contract_draft.txt").write_text("test")
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--operator-id", "test",
             "--tender-dir", str(temp),
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "technical_spec.txt" in result.stdout + result.stderr

    def test_missing_contract_draft_txt_fails(self):
        temp = Path("/tmp/pp1r_missing_contract")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        (temp / "01_raw_docs").mkdir()
        extracted = temp / "02_extracted_text"
        extracted.mkdir()
        (extracted / "notice.txt").write_text("test")
        (extracted / "technical_spec.txt").write_text("test")
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--operator-id", "test",
             "--tender-dir", str(temp),
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "contract_draft.txt" in result.stdout + result.stderr

    def test_missing_extracted_dir_fails(self):
        temp = Path("/tmp/pp1r_no_extracted_dir")
        shutil.rmtree(temp, ignore_errors=True)
        temp.mkdir(parents=True)
        result = subprocess.run(
            [sys.executable, str(SCRIPT),
             "--operator-id", "test",
             "--tender-dir", str(temp),
             "--provider", "stub"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
        assert "02_extracted_text" in result.stdout + result.stderr


# ---------------------------------------------------------------------------
# Export guard
# ---------------------------------------------------------------------------

class TestPP1RExportGuard:
    def test_internal_trace_redacted(self, tkp_output):
        _, tender = tkp_output
        export = json.loads((tender / "06_partner_export" / "export_summary.json").read_text())
        redacted = export.get("redacted_sections", [])
        assert any("runtime_trace" in r for r in redacted)

    def test_operator_decision_redacted(self, tkp_output):
        _, tender = tkp_output
        export = json.loads((tender / "06_partner_export" / "export_summary.json").read_text())
        redacted = export.get("redacted_sections", [])
        assert any("operator_decision" in r for r in redacted)

    def test_customer_report_included(self, tkp_output):
        _, tender = tkp_output
        export = json.loads((tender / "06_partner_export" / "export_summary.json").read_text())
        assert "customer_report" in export.get("included_sections", [])

    def test_export_summary_has_structure(self, tkp_output):
        _, tender = tkp_output
        export = json.loads((tender / "06_partner_export" / "export_summary.json").read_text())
        assert "included_sections" in export
        assert "redacted_sections" in export
        assert "export_status" in export


# ---------------------------------------------------------------------------
# Calibrated contract risk
# ---------------------------------------------------------------------------

class TestPP1RCalibratedRisk:
    def test_market_standard_terms_not_no_go(self, tkp_output):
        out, _ = tkp_output
        memo = (out / "calibrated_contract_risk_memo.md").read_text()
        assert "[STANDARD]" in memo
        assert "[DEAL-BREAKER]" in memo
        assert "[MATERIAL]" in memo

    def test_no_auto_no_go_phrasing(self, tkp_output):
        out, _ = tkp_output
        memo = (out / "calibrated_contract_risk_memo.md").read_text()
        assert "not automatic no-go" in memo.lower()

    def test_penalty_is_market_standard(self, tkp_output):
        out, _ = tkp_output
        memo = (out / "calibrated_contract_risk_memo.md").read_text()
        assert "STANDARD" in memo

    def test_security_is_material_risk(self, tkp_output):
        out, _ = tkp_output
        memo = (out / "calibrated_contract_risk_memo.md").read_text()
        assert "MATERIAL" in memo or "commercially_material" in memo


# ---------------------------------------------------------------------------
# No product catalog / known price assumptions
# ---------------------------------------------------------------------------

class TestPP1RNoProductCatalog:
    def test_rfq_draft_has_supplier_questions(self, tkp_output):
        out, _ = tkp_output
        rfq = (out / "rfq_request_draft.md").read_text()
        assert "price" in rfq.lower()
        assert "delivery" in rfq.lower()
        assert "warranty" in rfq.lower()
        assert "certificates" in rfq.lower()

    def test_operator_profile_no_prices_required(self):
        profile = (FIXTURE_DIR / "operator_profile.md").read_text()
        keywords = ["margin", "categories", "VAT", "regions", "SRO"]
        for kw in keywords:
            assert kw.lower() in profile.lower(), f"Missing keyword: {kw}"
        # Should NOT contain product-specific pricing
        negative = ["price per unit", "SKU", "product catalog", "fixed price"]
        for n in negative:
            assert n.lower() not in profile.lower(), f"Found product assumption: {n}"

    def test_requirements_have_no_product_catalog(self, tkp_output):
        out, _ = tkp_output
        reqs = json.loads((out / "requirements.json").read_text())
        for section in ["technical_requirements", "qualification_requirements"]:
            for item in reqs.get(section, []):
                assert "product line" not in item.lower()
                assert "price list" not in item.lower()

    def test_tkp_normalization_marks_review_or_parsed(self, tkp_output):
        out, _ = tkp_output
        quotes = json.loads((out / "tkp_normalized_quotes.json").read_text())
        for quote in quotes:
            assert quote.get("normalization_status") in {"parsed", "needs_review", "failed", "unsupported_format"}
            assert quote.get("human_review_required") is True

    def test_economics_uses_normalized_quote_totals(self, tkp_output):
        out, _ = tkp_output
        econ = json.loads((out / "economics_summary.json").read_text())
        assert econ.get("lowest_price") == 4200000.0


# ---------------------------------------------------------------------------
# No external actions
# ---------------------------------------------------------------------------

class TestPP1RNoExternalActions:
    def test_no_sqlalchemy_top_import(self):
        code = SCRIPT.read_text()
        assert "from sqlalchemy" not in code or "_try_llm_workflow_analysis" in code

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
# Synthetic fixture
# ---------------------------------------------------------------------------

class TestPP1RSyntheticFixture:
    def test_extracted_text_is_synthetic(self):
        for name in ["notice.txt", "technical_spec.txt", "contract_draft.txt"]:
            text = (TENDER_DIR / "02_extracted_text" / name).read_text()
            assert "synthetic" in text.lower() or "test" in text.lower()

    def test_operator_profile_is_synthetic(self):
        text = (FIXTURE_DIR / "operator_profile.md").read_text()
        assert "synthetic" in text.lower()

    def test_tkp_files_are_synthetic(self):
        for f in (TENDER_DIR / "04_tkp").iterdir():
            text = f.read_text()
            assert "synthetic" in text.lower() or "test" in text.lower()


# ---------------------------------------------------------------------------
# Docs
# ---------------------------------------------------------------------------

class TestPP1RDocs:
    def test_pp1r_sprint_spec_exists(self):
        assert (ROOT / "docs/product/PP1R_Tender_Operator_Pilot_Runner_Refinement.md").exists()

    def test_runbook_exists(self):
        assert (ROOT / "docs/product/Tender_Operator_Pilot_Runbook.md").exists()

    def test_risk_method_exists(self):
        assert (ROOT / "docs/product/Calibrated_Contract_Risk_Method.md").exists()

    def test_rfq_workflow_exists(self):
        assert (ROOT / "docs/product/Tender_Operator_RFQ_Workflow.md").exists()

    def test_operator_profile_template_exists(self):
        assert (ROOT / "docs/product/templates/Tender_Operator_Profile_Template.md").exists()

    def test_operator_folder_template_exists(self):
        assert (ROOT / "docs/product/templates/tender_operator_local_pilot_folder_template.md").exists()

    def test_runbook_no_auto(self):
        text = (ROOT / "docs/product/Tender_Operator_Pilot_Runbook.md").read_text()
        assert "No automated" in text or "manual" in text.lower()

    def test_risk_method_no_auto_no_go(self):
        text = (ROOT / "docs/product/Calibrated_Contract_Risk_Method.md").read_text()
        assert "not" in text and "automatic no-go" in text


# ---------------------------------------------------------------------------
# Backward compatibility
# ---------------------------------------------------------------------------

class TestPP1RBackwardCompat:
    def test_old_pp1_script_still_executable(self):
        assert OLD_PP1_SCRIPT.exists()
        code = OLD_PP1_SCRIPT.read_text()
        assert "partner" in code.lower() or "PP1" in code

    def test_old_pp1_docs_still_exist(self):
        assert (ROOT / "docs/product/Run_Partner_Tender_Folder.md").exists()
        assert (ROOT / "docs/product/templates/local_pilot_folder_template.md").exists()

    def test_old_pp1_tests_still_exist(self):
        assert (ROOT / "tests/test_partner_tender_folder_pp1.py").exists()

    def test_new_runbook_mentions_migration(self):
        text = (ROOT / "docs/product/Tender_Operator_Pilot_Runbook.md").read_text()
        assert "PP1" in text or "run_partner_tender_folder" in text or "backward compat" in text.lower()
