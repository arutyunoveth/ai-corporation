from scripts.r1.evaluate_golden_case import evaluate
from src.modules.hermes_agent.service import HermesProcurementAnalysisService


CASE = "0352300080626000109"
RUN = "r1-0352300080626000109-i01"


def _artifacts():
    doc = {"document_id": "doc-current", "tender_id": "t-current", "registry_number": CASE, "run_id": RUN, "processing_status": "extracted"}
    item = {"position_no": "1", "raw_name": "Диагностика", "quantity": "", "unit": "", "missing_reason": "quantity is not stated in NMCK table", "source_document_id": "doc-current", "source_quote": "Диагностика\tУсловная единица"}
    source = {"run_id": RUN, "documents": [doc]}
    extraction = {"run_id": RUN, "tender_id": "t-current", "procurement_kind": "services", "line_items": [item]}
    analysis = {"run_id": RUN, "line_items": [item]}
    report = {"run_id": RUN, "positions": [item]}
    return source, extraction, analysis, report


def test_cross_tender_evidence_is_rejected():
    source, extraction, analysis, report = _artifacts()
    extraction["line_items"][0]["source_document_id"] = "doc-other"
    result, defects = evaluate(registry_number=CASE, run_id=RUN, source_inventory=source, extraction=extraction, analysis=analysis, canonical_report=report, html="<h2>Что нужно поставить</h2>")
    assert result["status"] == "failed"
    assert any(defect["id"] == "EVD-003" for defect in defects["defects"])


def test_foreign_registry_number_causes_critical_failure():
    source, extraction, analysis, report = _artifacts()
    analysis["note"] = "foreign 0352300080626000110"
    result, defects = evaluate(registry_number=CASE, run_id=RUN, source_inventory=source, extraction=extraction, analysis=analysis, canonical_report=report, html="Что нужно поставить")
    assert result["status"] == "failed"
    assert any(defect["id"] == "TENANT-001" for defect in defects["defects"])


def test_global_memory_does_not_inject_factual_line_items():
    memory = {"memory_type": "feedback_error_case", "payload_json": {"line_items": [{"name": "foreign"}]}}
    assert not HermesProcurementAnalysisService._memory_is_safe_for_context(memory, "t-current")


def test_report_contains_supply_items():
    source, extraction, analysis, report = _artifacts()
    result, defects = evaluate(registry_number=CASE, run_id=RUN, source_inventory=source, extraction=extraction, analysis=analysis, canonical_report=report, html="<h2>Что нужно поставить</h2>")
    assert result["status"] == "passed"
    assert not defects["defects"]
