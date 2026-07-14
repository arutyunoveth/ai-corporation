from pathlib import Path
from lxml import html

from src.modules.tender_operator_agent_demo.report_model import build_procurement_report_model, canonical_report_to_markdown
from src.modules.tender_operator_agent_demo.upload_service import AnalyzedDocument, _build_output_payloads, _render_canonical_report_html


CASE = Path("tests/fixtures/golden/0352300080626000109")
NMCK = (CASE / "nmck_services_excerpt.txt").read_text(encoding="utf-8")
NOTICE = """<purchaseObjectInfo>Оказание услуг по диагностике, техническому обслуживанию и текущему ремонту автотранспортных средств</purchaseObjectInfo>
<OKPDCode>45.20</OKPDCode><maxPrice>500000.00</maxPrice>"""


def _model():
    metadata = {"run_id": "r1-report", "tender_title": "Оказание услуг по диагностике, техническому обслуживанию и текущему ремонту автотранспортных средств", "customer_name": None, "tender_category": "services", "status": "needs_review", "procurement_id": "0352300080626000109", "files": [{"file_id": "notice"}, {"file_id": "nmck"}], "warnings": [], "initial_price": 500000}
    documents = [AnalyzedDocument("Извещение.xml", ".xml", "notice", NOTICE, True, [], "getDocsIP", "notice"), AnalyzedDocument("Обоснование НМЦК.docx", ".docx", "supporting", NMCK, True, [], "getDocsIP", "nmck")]
    outputs = _build_output_payloads(metadata=metadata, documents=documents, analysis_mode="fallback_deterministic_adapter", requirements={}, calibrated_risks=[], supplier_questions=[], tkp_comparison=None, economics=None, bid_decision=None, core_complete=False, quote_inputs_present=False)
    return build_procurement_report_model(metadata, outputs)


def test_canonical_report_preserves_all_service_rows_unknowns_and_evidence():
    model = _model()
    assert model["metadata"]["service_item_count"] == 43
    assert model["metadata"]["analyzed_item_count"] == 43
    assert model["bid_decision"]["status"] == "needs_review"
    assert model["procurement_passport"]["okpd2"] == "45.20"
    assert all(row["quantity"] is None and row["quantity_display"] == "Не указан документацией" for row in model["service_catalog"])
    assert all(row["line_total"] is None for row in model["service_catalog"])
    assert any(row["original_name"] == "Капитальный ремонт двигателя" for row in model["service_catalog"])
    assert len(model["evidence_map"]) == 43


def test_canonical_web_and_export_text_have_same_critical_facts_without_prohibited_claims():
    model = _model()
    web, export = _render_canonical_report_html(model), canonical_report_to_markdown(model)
    for text in (web, export):
        assert "0352300080626000109" in text
        assert "45.20" in text
        assert "Капитальный ремонт двигателя" in text
        assert "Проект контракта отсутствует" in text
        assert "Не указан документацией" in text
        for forbidden in ("СМЭВ", "интеграц", "обучени", "преподавател", "аудитори"):
            assert forbidden.lower() not in text.lower()


def test_service_catalog_is_rendered_once_when_compatibility_rows_repeat_it():
    model = _model()
    document = html.fromstring(_render_canonical_report_html(model))
    tables = document.xpath("//table")
    service_tables = [table for table in tables if "Услуга" in " ".join(table.xpath(".//th//text()"))]
    compatibility_tables = [table for table in tables if "Наименование услуги" in " ".join(table.xpath(".//th//text()"))]
    rows = service_tables[0].xpath(".//tbody/tr")
    assert len(service_tables) == 1
    assert len(compatibility_tables) == 0
    assert len(rows) == len(model["service_catalog"]) == 43
    assert len({row.xpath("normalize-space(./td[2])") for row in rows}) == 43
    assert "Ключевые условия договора" in html.tostring(document, encoding="unicode")


def test_compatibility_table_remains_when_canonical_service_catalog_is_empty():
    model = _model()
    model["service_catalog"] = []
    model["compatibility_sections"]["spec_rows"] = [{"Наименование услуги": "Товар", "Единица": "шт."}]
    model["compatibility_sections"]["spec_columns"] = ["Наименование услуги", "Единица"]
    document = html.fromstring(_render_canonical_report_html(model))
    assert len(document.xpath("//table[.//th[contains(., 'Наименование услуги')]]")) == 1
