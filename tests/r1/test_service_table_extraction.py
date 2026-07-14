from pathlib import Path

from src.modules.tender_operator_agent_demo.upload_service import _extract_service_items_from_nmck_text


SOURCE = Path("tests/fixtures/golden/0352300080626000109/nmck_services_excerpt.txt")


def test_real_nmck_service_table_has_evidenced_unit_price_rows():
    items = _extract_service_items_from_nmck_text(SOURCE.read_text(encoding="utf-8"), "Обоснование НМЦК.docx")
    assert len(items) >= 41
    assert {item.name for item in items} >= {
        "Аппаратная промывка системы охлаждения",
        "Балансировка колес",
        "Капитальный ремонт двигателя",
    }
    assert all(item.item_type == "service" for item in items)
    assert all(item.quantity is None and item.quantity_status == "not_specified" for item in items)
    assert all(item.unit_price and item.total_price is None for item in items)
    assert all(item.evidence_id and item.source_row_number and item.raw_fragment for item in items)


def test_service_table_deterministic_and_excludes_total_and_note_rows():
    text = SOURCE.read_text(encoding="utf-8")
    first = _extract_service_items_from_nmck_text(text, "Обоснование НМЦК.docx")
    second = _extract_service_items_from_nmck_text(text, "Обоснование НМЦК.docx")
    assert [(item.name, item.evidence_id) for item in first] == [(item.name, item.evidence_id) for item in second]
    assert not any("максимальное значение" in item.name.lower() for item in first)
    assert not any("начальная сумма" in item.name.lower() for item in first)


def test_service_parser_handles_headers_notes_and_multiline_names():
    text = """Наименование услуг\tЕдиница измерения\tЦена единицы
Диагностика\nтормозной системы\tУсловная единица\t1 900,00
Итого\t\t500 000,00
Под одной условной единицей понимается один норма-час
"""
    items = _extract_service_items_from_nmck_text(text, "nmck.docx")
    assert [item.name for item in items] == ["Диагностика тормозной системы"]
