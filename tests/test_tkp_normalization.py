import json
from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import select

from src.modules.quote_repository.tkp_normalization import (
    build_tkp_comparison_from_normalized_quotes,
    build_tkp_llm_inputs,
    build_tkp_normalization_report,
    normalize_tkp_quotes,
)
from src.modules.supplier_registry.models import SupplierContact, SupplierExternalRef, SupplierProfile
from src.shared.enums import SupplierStatus
from src.shared.ids import next_supplier_id


def _seed_supplier(session, *, legal_name: str, display_name: str, inn: str, email: str | None = None, website: str | None = None) -> SupplierProfile:
    supplier = SupplierProfile(
        supplier_id=next_supplier_id(session, SupplierProfile.supplier_id),
        legal_name=legal_name,
        display_name=display_name,
        inn=inn,
        country_code="RU",
        status=SupplierStatus.ACTIVE,
        notes="seeded",
    )
    session.add(supplier)
    session.flush()
    if email:
        session.add(
            SupplierContact(
                supplier_id=supplier.supplier_id,
                contact_name="Sales",
                email=email,
                phone=None,
                is_primary=True,
            )
        )
    if website:
        session.add(SupplierExternalRef(supplier_id=supplier.supplier_id, ref_type="website", ref_value=website))
    session.commit()
    return supplier


def test_normalize_tkp_markdown_extracts_structured_quote(session, tmp_path: Path):
    supplier = _seed_supplier(
        session,
        legal_name='ООО "Supplier Alpha"',
        display_name="Supplier Alpha",
        inn="7701234567",
        email="sales@supplier-alpha.test",
    )
    tkp_file = tmp_path / "supplier_alpha_tkp.md"
    tkp_file.write_text(
        "\n".join(
            [
                "# TKP - Supplier Alpha",
                "- Total price: 4,500,000 RUB",
                "- Delivery time: 30 calendar days",
                "- Warranty: 36 months",
                "- Payment terms: 50% prepayment, 50% after delivery",
                "- Contact: sales@supplier-alpha.test",
            ]
        ),
        encoding="utf-8",
    )

    quotes = normalize_tkp_quotes(session, tkp_files=[tkp_file])
    quote = quotes[0]

    assert quote.supplier_id == supplier.supplier_id
    assert quote.total_amount == 4500000.0
    assert quote.delivery_time_days == 30
    assert quote.warranty_months == 36
    assert quote.payment_terms is not None
    assert quote.normalization_status in {"parsed", "needs_review"}
    assert quote.human_review_required is True


def test_normalize_tkp_xlsx_builds_line_items_and_comparison(session, tmp_path: Path):
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Наименование", "Количество", "Ед. изм.", "Цена", "Сумма", "Срок поставки", "Условия оплаты"])
    sheet.append(["Шкаф управления", 2, "шт", 120000, 240000, "35 дней", "100% postpay"])
    sheet.append(["Кабель", 100, "м", 450, 45000, "20 дней", "100% postpay"])
    xlsx_path = tmp_path / "supplier_beta_quote.xlsx"
    workbook.save(xlsx_path)

    quotes = normalize_tkp_quotes(session, tkp_files=[xlsx_path])
    quote = quotes[0]

    assert len(quote.line_items) == 2
    assert quote.total_amount == 285000.0
    assert quote.line_items[0].item_name == "Шкаф управления"

    comparison = build_tkp_comparison_from_normalized_quotes(quotes, analysis_mode="stub", method="deterministic_normalized")
    assert comparison["supplier_quotes_found"] == 1
    assert comparison["items_extracted"] == 2
    assert comparison["suppliers"][0]["total_amount"] == 285000.0


def test_build_tkp_llm_inputs_supports_text_and_spreadsheets(tmp_path: Path):
    text_file = tmp_path / "supplier_text.md"
    text_file.write_text("Total price: 100000 RUB", encoding="utf-8")

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Наименование", "Количество", "Цена"])
    sheet.append(["Кабель", 100, 450])
    xlsx_path = tmp_path / "supplier_sheet.xlsx"
    workbook.save(xlsx_path)

    inputs = build_tkp_llm_inputs([text_file, xlsx_path])

    assert len(inputs) == 2
    assert any(item["source_file"].endswith("supplier_text.md") for item in inputs)
    assert any(item["source_file"].endswith("supplier_sheet.xlsx") for item in inputs)


def test_tkp_report_mentions_review_fields(session, tmp_path: Path):
    txt_file = tmp_path / "quote.txt"
    txt_file.write_text("Offer validity: 30 days\nPayment terms: after delivery", encoding="utf-8")

    quotes = normalize_tkp_quotes(session, tkp_files=[txt_file])
    report = build_tkp_normalization_report(quotes)

    assert "Fields needing review" in report
    assert "quote.txt" in report
    json.dumps([quote.model_dump() for quote in quotes], ensure_ascii=False)
