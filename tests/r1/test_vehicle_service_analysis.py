import json
import subprocess
import sys
from pathlib import Path

from src.modules.tender_operator_agent_demo.upload_service import (
    AnalyzedDocument,
    _build_preliminary_procurement_analysis,
    _build_output_payloads,
)


CASE = Path("tests/fixtures/golden/0352300080626000109")
NMCK = (CASE / "nmck_services_excerpt.txt").read_text(encoding="utf-8")
NOTICE = """<purchaseObjectInfo>Оказание услуг по диагностике, техническому обслуживанию и текущему ремонту автотранспортных средств</purchaseObjectInfo>
<OKPDCode>45.20</OKPDCode><maxPrice>500000.00</maxPrice>"""


def _documents():
    return [
        AnalyzedDocument("Извещение.xml", ".xml", "notice", NOTICE, True, [], "getDocsIP", "notice"),
        AnalyzedDocument("Обоснование НМЦК.docx", ".docx", "supporting", NMCK, True, [], "getDocsIP", "nmck"),
    ]


def test_vehicle_service_analysis_preserves_real_rows_and_unknown_contract_terms():
    analysis = _build_preliminary_procurement_analysis(
        metadata={"tender_title": "Документация ЕИС", "procurement_id": "not-used", "initial_price": 500000},
        documents=_documents(),
        technical_spec_text="",
        contract_draft_text="",
        notice_text=NOTICE,
    )

    assert analysis["procurement_kind"] == "services"
    assert analysis["domain_profile"] == "vehicle_maintenance_services"
    assert analysis["item_coverage"] == {
        "extracted_item_count": 43,
        "analyzed_item_count": 43,
        "ignored_item_count": 0,
        "item_evidence_coverage": 1.0,
        "grouping_coverage": 1.0,
    }
    assert any(item["original_name"] == "Капитальный ремонт двигателя" for item in analysis["service_items"])
    assert all(item["quantity"] is None and item["quantity_status"] == "not_specified" for item in analysis["service_items"])
    assert all(item["evidence_ids"] for item in analysis["service_items"])
    assert analysis["missing_documents"] == ["draft_contract"]


def test_services_output_rejects_training_and_integration_fallback_claims():
    metadata = {
        "run_id": "r1-test",
        "tender_title": "Оказание услуг по диагностике, техническому обслуживанию и текущему ремонту автотранспортных средств",
        "customer_name": "Заказчик",
        "tender_category": "services",
        "status": "needs_review",
        "procurement_id": "test",
        "files": [],
        "warnings": [],
    }
    outputs = _build_output_payloads(
        metadata=metadata,
        documents=_documents(),
        analysis_mode="fallback_deterministic_adapter",
        requirements={},
        calibrated_risks=[],
        supplier_questions=[],
        tkp_comparison=None,
        economics=None,
        bid_decision=None,
        core_complete=False,
        quote_inputs_present=False,
    )
    rendered = str(outputs).lower()
    for prohibited in ("смэв", "интеграц", "обучени", "преподавател", "аудитори", "сэмд"):
        assert prohibited not in rendered
    assert outputs["final_recommendation"]["recommendation"] != "participate_conditionally"
    assert outputs["economics"]["expected_revenue"] is None
    assert outputs["economics"]["gross_margin_percent"] is None
    assert outputs["requirements"]["analysis_context"]["unknown_contract_terms"]


def test_golden_analysis_evaluator_accepts_source_backed_service_candidate(tmp_path):
    metadata = {
        "run_id": "r1-test", "tender_title": "Оказание услуг по диагностике, техническому обслуживанию и текущему ремонту автотранспортных средств",
        "customer_name": "Заказчик", "tender_category": "services", "status": "needs_review", "procurement_id": "test", "files": [], "warnings": [],
    }
    candidate = _build_output_payloads(
        metadata=metadata, documents=_documents(), analysis_mode="fallback_deterministic_adapter", requirements={},
        calibrated_risks=[], supplier_questions=[], tkp_comparison=None, economics=None, bid_decision=None,
        core_complete=False, quote_inputs_present=False,
    )
    candidate_path = tmp_path / "candidate.json"
    candidate_path.write_text(json.dumps(candidate, ensure_ascii=False), encoding="utf-8")
    completed = subprocess.run(
        [sys.executable, "scripts/r1/evaluate_golden_analysis.py", "--case", str(CASE), "--candidate", str(candidate_path)],
        text=True, capture_output=True, check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
