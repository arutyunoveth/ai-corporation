from __future__ import annotations

from pathlib import Path

from src.modules.tender_operator_agent_demo.case_set_validation import compare_case_ids
from src.modules.tender_operator_agent_demo.eis_notice_parser import extract_notice_metadata, merge_structured_metadata
from src.modules.tender_operator_agent_demo.report_model import build_procurement_report_model, canonical_report_to_markdown
from src.modules.tender_operator_agent_demo.report_export_service import _build_docx_from_canonical, _build_pdf_from_canonical
from src.modules.tender_operator_agent_demo.upload_service import _extract_supply_items_from_notification_xml, _render_canonical_report_html


NOTICE_XML = """<notification><publishDTInEIS>2026-07-07T12:38:12.345+10:00</publishDTInEIS><endDT>2026-07-15T12:00:00+10:00</endDT><purchaseObjectInfo>Официальное название закупки</purchaseObjectInfo><initialPrice>1234.50</initialPrice><purchaseObjects><purchaseObject><type>GOODS</type><KTRU><name>Препарат альфа</name></KTRU><OKEI><nationalCode>шт</nationalCode><name>штука</name></OKEI><quantity><value>12</value></quantity><price>10</price><sum>120</sum></purchaseObject><purchaseObject><type>GOODS</type><KTRU><name>Препарат бета</name></KTRU><OKEI><nationalCode>упак</nationalCode></OKEI><quantity></quantity><price>20</price><sum>20</sum></purchaseObject></purchaseObjects></notification>"""


def _outputs(items: list[dict]) -> dict[str, dict]:
    return {
        "requirements": {"preliminary_analysis": {"supply_items": items, "item_coverage": {}, "next_actions": []}, "analysis_context": {"procurement_subject": "Официальное название закупки", "nmck": 1234.5, "currency": "RUB", "document_coverage": "available", "missing_documents": []}},
        "final_recommendation": {"recommendation": "needs_review", "rationale": [], "manual_checks": []},
        "contract_risks": {"risks": []}, "economics": {"metrics": [], "warnings": []},
        "supplier_questions": {"questions": []}, "quotes_comparison": {"highlights": []},
    }


def test_notice_prefers_publish_and_end_datetime_and_official_subject():
    result = extract_notice_metadata(NOTICE_XML)
    assert result["publication_date"] == "07.07.2026 12:38:12.345 +10:00"
    assert result["submission_deadline"] == "15.07.2026 12:00:00 +10:00"
    assert result["procurement_subject"] == "Официальное название закупки"


def test_notice_merge_keeps_field_level_source_references():
    merged = merge_structured_metadata(extract_notice_metadata(NOTICE_XML), {"publication_date": "01.01.2000"}, {})
    assert merged["publication_date"]["source"] == "eis_notice"
    assert merged["publication_date"]["source_reference"] == "eis_notice:publication_date"


def test_notification_xml_extracts_nested_name_quantity_and_unit():
    items = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")
    assert [(item.name, item.quantity, item.unit) for item in items] == [("Препарат альфа", "12", "шт"), ("Препарат бета", None, "упак")]


def test_missing_quantity_is_explicit_not_specified():
    items = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")
    assert items[1].quantity_status == "not_specified"


def test_source_quantity_is_specified_and_units_are_not_summed():
    items = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")
    assert items[0].quantity_status == "specified"
    assert [item.unit for item in items] == ["шт", "упак"]


def test_canonical_model_exposes_mandatory_procurement_fields_and_line_items():
    items = [item.__dict__ for item in _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")]
    metadata = {"run_id": "run-1", "procurement_id": "expected-number", "publication_date": "07.07.2026 12:38:12.345 +10:00", "deadline": "15.07.2026 12:00:00 +10:00", "tender_title": "demo", "procurement_title": "Официальное название закупки", "files": [], "customer_name": "Заказчик"}
    model = build_procurement_report_model(metadata, _outputs(items))
    assert model["procurement_title"] == "Официальное название закупки"
    assert model["procurement_number"] == "expected-number"
    assert model["publication_datetime"] == metadata["publication_date"]
    assert model["application_deadline"] == metadata["deadline"]
    assert len(model["line_items"]) == 2


def test_positions_count_is_line_item_count_not_document_count():
    items = [item.__dict__ for item in _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")]
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "files": ["a", "b", "c"]}, _outputs(items))
    assert model["compatibility_sections"]["positions_count"] == 2


def test_markdown_contains_title_dates_deadline_quantity_unit_and_evidence():
    item = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")[0].__dict__
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "publication_date": "07.07.2026 12:38:12.345 +10:00", "deadline": "15.07.2026 12:00:00 +10:00", "files": []}, _outputs([item]))
    text = canonical_report_to_markdown(model)
    assert all(value in text for value in ("Официальное название закупки", "07.07.2026 12:38:12.345 +10:00", "15.07.2026 12:00:00 +10:00", "Препарат альфа", "12", "шт"))
    assert item["evidence_id"] in text


def test_web_renderer_consumes_canonical_line_items_and_required_fields():
    item = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")[0].__dict__
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "publication_date": "pub", "deadline": "end", "files": []}, _outputs([item]))
    rendered = _render_canonical_report_html(model)
    assert all(value in rendered for value in ("Официальное название закупки", "pub", "end", "Препарат альфа", "шт"))


def test_docx_renderer_contains_same_canonical_fields(tmp_path: Path):
    from docx import Document
    item = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")[0].__dict__
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "publication_date": "pub", "deadline": "end", "files": []}, _outputs([item]))
    path = tmp_path / "report.docx"
    _build_docx_from_canonical(model, "title", path)
    text = "\n".join(p.text for p in Document(path).paragraphs)
    assert all(value in text for value in ("Официальное название закупки", "pub", "end", "Препарат альфа"))


def test_pdf_renderer_contains_same_canonical_fields(tmp_path: Path):
    import subprocess
    item = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")[0].__dict__
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "publication_date": "pub", "deadline": "end", "files": []}, _outputs([item]))
    path = tmp_path / "report.pdf"
    _build_pdf_from_canonical(model, "title", path)
    text = subprocess.run(["pdftotext", str(path), "-"], check=True, capture_output=True, text=True).stdout
    assert all(value in text for value in ("Официальное название закупки", "pub", "end", "Препарат альфа"))


def test_case_set_validation_detects_mismatch_without_number_specific_branching():
    result = compare_case_ids(["case-a", "case-b"], ["case-a", "case-c"])
    assert result["missing"] == ["case-b"]
    assert result["unexpected"] == ["case-c"]
    assert result["is_match"] is False


def test_case_set_validation_accepts_corrected_observed_set():
    result = compare_case_ids(["case-a", "case-b"], ["case-b", "case-a"])
    assert result["is_match"] is True


def test_canonical_model_preserves_unknown_quantity_instead_of_inventing_value():
    item = _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")[1].__dict__
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "files": []}, _outputs([item]))
    assert model["line_items"][0]["quantity"] is None
    assert model["line_items"][0]["quantity_status"] == "not_specified"
    assert model["line_items"][0]["quantity_display"] == "Не указан документацией"


def test_xlsx_ktru_column_does_not_shift_unit_into_quantity():
    from src.modules.tender_operator_agent_demo.upload_service import _extract_supply_items_from_xlsx_text
    text = "1\tЛекарственный препарат\t21.20.10.141-000044\tштука\t123\t10\t1230"
    item = _extract_supply_items_from_xlsx_text(text, "nmck.xlsx")[0]
    assert (item.name, item.quantity, item.unit, item.ktru) == ("Лекарственный препарат", "123", "шт", "21.20.10.141-000044")


def test_standard_and_technical_requirement_rows_are_not_line_items():
    from src.modules.tender_operator_agent_demo.upload_service import _extract_supply_items_from_xlsx_text
    text = "1\tГОСТ 31996-2012\tшт\t1\n2\tТребования к упаковке\tшт\t1\n3\tКабель силовой АВВГ\tм\t2200"
    items = _extract_supply_items_from_xlsx_text(text, "spec.xlsx")
    assert [(item.name, item.quantity, item.unit) for item in items] == [("Кабель силовой АВВГ", "2200", "м")]


def test_same_name_with_different_quantity_is_not_merged():
    from src.modules.tender_operator_agent_demo.upload_service import SupplyItem, _merge_supply_items
    rows = [
        SupplyItem(None, "Кабель", "10", "м", [], [], None, "a.xlsx", "nmck_xlsx", "high", "", source_row_number=1),
        SupplyItem(None, "Кабель", "20", "м", [], [], None, "a.xlsx", "nmck_xlsx", "high", "", source_row_number=2),
    ]
    assert [item.quantity for item in _merge_supply_items(rows)] == ["10", "20"]


def test_structured_notice_extracts_customer_and_delivery_place():
    xml = """<n><customer><fullName>ГБУ Заказчик</fullName><INN>123</INN><KPP>456</KPP></customer><deliveryPlacesInfo><GARAddress>Край, город, улица 1</GARAddress></deliveryPlacesInfo></n>"""
    result = extract_notice_metadata(xml)
    assert result["customer_name"] == "ГБУ Заказчик"
    assert result["customer_inn"] == "123"
    assert result["customer_kpp"] == "456"
    assert result["delivery_place"] == "Край, город, улица 1"


def test_structured_notice_extracts_explicit_okpd2_with_source_type():
    xml = """<n><OKPD2><OKPDCode>27.11.50.120</OKPDCode><OKPDName>Установки электрогенераторные</OKPDName></OKPD2></n>"""
    assert extract_notice_metadata(xml)["okpd2_codes"] == [{"code": "27.11.50.120", "name": "Установки электрогенераторные", "source_type": "structured_notice_xml"}]


def test_known_volume_uses_row_quantities_without_summing_units():
    first, second = [item.__dict__ for item in _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")]
    second["quantity"] = "5"
    context = _outputs([first, second])["requirements"]["analysis_context"]
    context["procurement_category"] = "goods"
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "files": []}, _outputs([first, second]))
    # The test payload uses a separate context instance; the production rule is
    # asserted directly with an explicit goods context below.
    outputs = _outputs([first, second]); outputs["requirements"]["analysis_context"]["procurement_category"] = "goods"
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "files": []}, outputs)
    assert model["procurement_volume_status"] == "known"
    assert "Неизвестен фактический объём" not in model["limitations"]


def test_partial_volume_keeps_volume_reason():
    items = [item.__dict__ for item in _extract_supply_items_from_notification_xml(NOTICE_XML, "notice.xml")]
    outputs = _outputs(items); outputs["requirements"]["analysis_context"]["procurement_category"] = "goods"
    model = build_procurement_report_model({"run_id": "run-1", "procurement_id": "n", "files": []}, outputs)
    assert model["procurement_volume_status"] == "partially_known"
    assert "Неизвестен фактический объём" in model["limitations"]


def test_cross_source_items_merge_and_keep_quantity_and_evidence():
    from src.modules.tender_operator_agent_demo.upload_service import SupplyItem, _merge_supply_items

    xml = SupplyItem(None, "Бикрост", "10", "рулон", [], [], None, "notice.xml", "notification_xml", "high", "", evidence_id="ev-xml", name_source_type="structured_direct_name")
    xlsx = SupplyItem(None, "Бикрост", None, "рулон", [], [], None, "НМЦК.xlsx", "xlsx", "medium", "", evidence_id="ev-xlsx")

    merged = _merge_supply_items([xml, xlsx])

    assert len(merged) == 1
    assert merged[0].quantity == "10"
    assert set(merged[0].evidence_ids) == {"ev-xml", "ev-xlsx"}


def test_works_scope_is_not_overwritten_by_equipment_mentions():
    from src.modules.tender_operator_agent_demo.upload_service import _infer_procurement_kind

    assert _infer_procurement_kind("Выполнение работ по замене электротехнического оборудования, монтаж и смета") == "works"


def test_work_scope_wins_over_supply_contract_boilerplate():
    from src.modules.tender_operator_agent_demo.upload_service import _infer_procurement_kind

    assert _infer_procurement_kind(
        "Техническое задание на поставку оборудования",
        "Поставщик обязуется поставить товар",
        "ОКПД2: Работы электромонтажные",
        "Замена электротехнического оборудования на объекте инфраструктуры",
    ) == "works"
