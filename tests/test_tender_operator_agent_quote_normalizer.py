from io import BytesIO

from openpyxl import Workbook

from src.modules.tender_operator_agent_demo.quote_normalizer import (
    SpreadsheetSource,
    build_economics_summary,
    build_quote_comparison,
)


def _workbook_bytes(headers: list[str], rows: list[list[object]]) -> bytes:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Sheet1"
    sheet.append(headers)
    for row in rows:
        sheet.append(row)
    stream = BytesIO()
    workbook.save(stream)
    return stream.getvalue()


def _source(name: str, payload: bytes) -> SpreadsheetSource:
    return SpreadsheetSource(
        file_id=name,
        display_name=name,
        source_file=name,
        extension=".xlsx",
        raw_content=payload,
        source="upload",
    )


def test_quote_normalizer_recognizes_russian_headers():
    payload = _workbook_bytes(
        ["№", "Наименование", "Кол-во", "Ед. изм.", "Цена", "Сумма", "Срок поставки", "Валюта"],
        [[1, "Шкаф управления", 2, "шт", 120000, 240000, "35 дней", "RUB"]],
    )

    comparison = build_quote_comparison([_source("ТКП_ПоставщикА.xlsx", payload)], "controlled_runner_adapter")

    assert comparison.supplier_quotes_found == 1
    assert comparison.items_extracted == 1
    assert comparison.suppliers[0].supplier_name
    assert comparison.items[0].offers[0].unit_price == 120000


def test_quote_normalizer_recognizes_english_headers():
    payload = _workbook_bytes(
        ["Item", "Description", "Quantity", "Unit", "Unit Price", "Amount", "Delivery", "Currency"],
        [[1, "Cable", 100, "m", 450, 45000, "20 days", "RUB"]],
    )

    comparison = build_quote_comparison([_source("quote_supplier_b.xlsx", payload)], "controlled_runner_adapter")

    assert comparison.supplier_quotes_found == 1
    assert comparison.items[0].offers[0].offered_name == "Cable"


def test_quote_comparison_returns_suppliers_and_items():
    supplier_a = _workbook_bytes(
        ["№", "Наименование", "Кол-во", "Ед. изм.", "Цена", "Сумма", "Валюта"],
        [[1, "Шкаф управления", 2, "шт", 120000, 240000, "RUB"]],
    )
    supplier_b = _workbook_bytes(
        ["№", "Наименование", "Кол-во", "Ед. изм.", "Цена", "Сумма", "Валюта"],
        [[1, "Шкаф управления", 2, "шт", 110000, 220000, "RUB"]],
    )

    comparison = build_quote_comparison(
        [_source("ТКП_ПоставщикА.xlsx", supplier_a), _source("ТКП_ПоставщикБ.xlsx", supplier_b)],
        "controlled_runner_adapter",
    )

    assert comparison.supplier_quotes_found == 2
    assert comparison.items[0].best_price_supplier
    assert comparison.items[0].price_spread_percent is not None


def test_economics_returns_insufficient_data_without_quotes():
    comparison = build_quote_comparison([], "fallback_deterministic_adapter")

    economics = build_economics_summary(
        quote_comparison=comparison,
        analysis_mode="fallback_deterministic_adapter",
        target_margin_percent=15,
        logistics_reserve_percent=3,
        risk_reserve_percent=5,
        payment_delay_days=45,
    )

    assert economics.economics_status == "insufficient_data"
    assert economics.status == "blocked"


def test_economics_returns_conditionally_viable_with_supplier_costs():
    supplier_a = _workbook_bytes(
        ["№", "Наименование", "Кол-во", "Ед. изм.", "Цена", "Сумма", "Валюта"],
        [[1, "Шкаф управления", 2, "шт", 120000, 240000, "RUB"]],
    )
    comparison = build_quote_comparison([_source("ТКП_ПоставщикА.xlsx", supplier_a)], "controlled_runner_adapter")

    economics = build_economics_summary(
        quote_comparison=comparison,
        analysis_mode="controlled_runner_adapter",
        target_margin_percent=15,
        logistics_reserve_percent=3,
        risk_reserve_percent=5,
        payment_delay_days=45,
    )

    assert economics.economics_status == "conditionally_viable"
    assert economics.preliminary_bid_price is not None
    assert economics.supplier_cost_selected == 240000


def test_unsupported_excel_structure_returns_partial_not_crash():
    payload = _workbook_bytes(["foo", "bar"], [["abc", "def"]])

    comparison = build_quote_comparison([_source("unknown.xlsx", payload)], "controlled_runner_adapter")

    assert comparison.status in {"needs_review", "blocked", "partial"}
    assert comparison.supplier_quotes_found == 0
