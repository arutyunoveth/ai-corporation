from pathlib import Path

from openpyxl import Workbook
from sqlalchemy import select

from src.modules.supplier_registry.models import SupplierContact, SupplierExternalRef, SupplierProfile, SupplierTag
from src.modules.supplier_registry.vendor_import import (
    build_vendor_import_report_markdown,
    import_vendor_list,
)
from src.shared.enums import SupplierStatus
from src.shared.ids import next_supplier_id


def _seed_supplier(session, *, legal_name: str, display_name: str, inn: str, website: str | None = None) -> SupplierProfile:
    supplier = SupplierProfile(
        supplier_id=next_supplier_id(session, SupplierProfile.supplier_id),
        legal_name=legal_name,
        display_name=display_name,
        inn=inn,
        country_code="RU",
        status=SupplierStatus.ACTIVE,
        notes="Seeded supplier",
    )
    session.add(supplier)
    session.flush()
    if website:
        session.add(SupplierExternalRef(supplier_id=supplier.supplier_id, ref_type="website", ref_value=website))
    session.commit()
    return supplier


def test_import_vendor_list_csv_creates_supplier_entities(session, tmp_path: Path):
    csv_path = tmp_path / "vendor_list.csv"
    csv_path.write_text(
        "\n".join(
            [
                "Юридическое лицо,Название,ИНН,Сайт,Email,Телефон,Категории,Бренды,Регион,Комментарий",
                '"ООО ""Электро Поставка""",ЭлектроПоставка,7701234567,electro.example.com,Sales@Electro.Example.com,+7 (495) 111-22-33,"Electro, Automation",IEK,Moscow,Preferred vendor',
            ]
        ),
        encoding="utf-8",
    )

    summary = import_vendor_list(
        session,
        operator_id="tender_operator_001",
        file_path=csv_path,
        source_label="vendor-list-2026-07",
    )

    assert summary.total_rows == 1
    assert summary.created_suppliers == 1
    assert summary.updated_suppliers == 0
    assert summary.skipped_rows == 0
    assert summary.rows_without_inn == 0
    assert summary.contacts_created == 1

    supplier = session.scalar(select(SupplierProfile).where(SupplierProfile.inn == "7701234567"))
    assert supplier is not None
    assert supplier.display_name == "ЭлектроПоставка"
    assert supplier.status == SupplierStatus.ACTIVE

    contacts = list(session.scalars(select(SupplierContact).where(SupplierContact.supplier_id == supplier.supplier_id)))
    assert len(contacts) == 1
    assert contacts[0].email == "sales@electro.example.com"
    assert contacts[0].is_primary is True

    refs = list(session.scalars(select(SupplierExternalRef).where(SupplierExternalRef.supplier_id == supplier.supplier_id)))
    ref_pairs = {(ref.ref_type, ref.ref_value) for ref in refs}
    assert ("website", "https://electro.example.com") in ref_pairs
    assert ("vendor_list_source", "vendor-list-2026-07|vendor_list.csv") in ref_pairs
    assert ("vendor_list_row", "2") in ref_pairs

    tags = {
        tag.tag_code
        for tag in session.scalars(select(SupplierTag).where(SupplierTag.supplier_id == supplier.supplier_id))
    }
    assert "SOURCE_VENDOR_LIST" in tags
    assert "OPERATOR_TENDER_OPERATOR_001" in tags
    assert "CATEGORY_ELECTRO" in tags
    assert "CATEGORY_AUTOMATION" in tags
    assert "BRAND_IEK" in tags
    assert "REGION_MOSCOW" in tags


def test_import_vendor_list_xlsx_updates_existing_and_marks_review_rows(session, tmp_path: Path):
    existing = _seed_supplier(
        session,
        legal_name='ООО "Акме Электро"',
        display_name="Акме Электро",
        inn="7707654321",
        website="https://acme.ru",
    )

    workbook = Workbook()
    sheet = workbook.active
    sheet.append(
        [
            "Наименование",
            "Отображаемое название",
            "ИНН",
            "Сайт",
            "Почта",
            "Телефон",
            "Категория",
            "Производители",
            "Город",
            "Примечание",
        ]
    )
    sheet.append(
        [
            'ООО "Акме Электро"',
            "Акме Электро",
            "7707654321",
            "https://acme.ru/catalog",
            "rfq@acme.ru",
            "+7 495 777 88 99",
            "Electro",
            "IEK",
            "Moscow",
            "Updated from July list",
        ]
    )
    sheet.append(
        [
            "Акме Электро",
            "",
            "",
            "acme.ru",
            "sales@acme.ru",
            "",
            "Electro",
            "",
            "Moscow",
            "No INN yet",
        ]
    )
    sheet.append(["", "", "", "", "", "", "", "", "", ""])

    xlsx_path = tmp_path / "vendor_list.xlsx"
    workbook.save(xlsx_path)

    summary = import_vendor_list(
        session,
        operator_id="tender_operator_001",
        file_path=xlsx_path,
        source_label="vendor-list-xlsx",
    )

    assert summary.total_rows == 3
    assert summary.created_suppliers == 1
    assert summary.updated_suppliers == 1
    assert summary.skipped_rows == 1
    assert summary.rows_without_inn == 1
    assert summary.possible_duplicates >= 1
    assert summary.contacts_created == 2

    suppliers = list(session.scalars(select(SupplierProfile).order_by(SupplierProfile.created_at.asc())))
    assert len(suppliers) == 2

    updated = session.scalar(select(SupplierProfile).where(SupplierProfile.supplier_id == existing.supplier_id))
    assert updated is not None
    assert "Updated from July list" in (updated.notes or "")

    synthetic = session.scalar(select(SupplierProfile).where(SupplierProfile.inn.like("NOINN-%")))
    assert synthetic is not None
    assert synthetic.status == SupplierStatus.DRAFT

    synthetic_tags = {
        tag.tag_code
        for tag in session.scalars(select(SupplierTag).where(SupplierTag.supplier_id == synthetic.supplier_id))
    }
    assert "NEEDS_REVIEW_NO_INN" in synthetic_tags
    assert "POSSIBLE_DUPLICATE_VENDOR_LIST" in synthetic_tags
    assert "SOURCE_VENDOR_LIST" in synthetic_tags

    report = build_vendor_import_report_markdown(summary)
    assert "Possible duplicate candidates found" in report
    assert "INN is missing; supplier tagged for review" in report
    assert "Row skipped because supplier name is missing" in report
