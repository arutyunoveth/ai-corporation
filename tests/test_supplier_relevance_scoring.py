from src.modules.supplier_registry.models import SupplierContact, SupplierExternalRef, SupplierProfile, SupplierTag
from src.modules.supplier_search.service import (
    build_context_from_requirements,
    get_supplier_sourcing_snapshot,
    rank_suppliers_for_context,
)
from src.shared.enums import SupplierStatus
from src.shared.ids import next_supplier_id


def _create_supplier(
    session,
    *,
    legal_name: str,
    display_name: str,
    inn: str,
    status: SupplierStatus,
    tags: list[str],
    email: str | None = None,
    phone: str | None = None,
    website: str | None = None,
) -> SupplierProfile:
    supplier = SupplierProfile(
        supplier_id=next_supplier_id(session, SupplierProfile.supplier_id),
        legal_name=legal_name,
        display_name=display_name,
        inn=inn,
        country_code="RU",
        status=status,
        notes="Seeded for scoring",
    )
    session.add(supplier)
    session.flush()
    if email or phone:
        session.add(
            SupplierContact(
                supplier_id=supplier.supplier_id,
                contact_name="Sales",
                email=email,
                phone=phone,
                is_primary=True,
            )
        )
    if website:
        session.add(SupplierExternalRef(supplier_id=supplier.supplier_id, ref_type="website", ref_value=website))
    for tag in tags:
        session.add(SupplierTag(supplier_id=supplier.supplier_id, tag_code=tag))
    session.commit()
    return supplier


def test_rank_suppliers_prioritizes_vendor_list_relevance(session):
    relevant = _create_supplier(
        session,
        legal_name='ООО "Электро Снабжение"',
        display_name="Электро Снабжение",
        inn="7701111111",
        status=SupplierStatus.ACTIVE,
        tags=[
            "CATEGORY_ELECTRO",
            "BRAND_IEK",
            "REGION_MOSCOW",
            "SOURCE_VENDOR_LIST",
            "TENDER_READY",
        ],
        email="sales@electro.ru",
        phone="+7 495 111-22-33",
        website="https://electro.ru",
    )
    _create_supplier(
        session,
        legal_name='ООО "Мебель Торг"',
        display_name="Мебель Торг",
        inn="7702222222",
        status=SupplierStatus.ACTIVE,
        tags=["CATEGORY_FURNITURE", "REGION_SPB"],
        email=None,
        phone=None,
        website=None,
    )
    _create_supplier(
        session,
        legal_name='ООО "Электро Проверка"',
        display_name="Электро Проверка",
        inn="NOINN-123456789ABC",
        status=SupplierStatus.DRAFT,
        tags=["CATEGORY_ELECTRO", "SOURCE_VENDOR_LIST", "NEEDS_REVIEW_NO_INN"],
        email="draft@electro.ru",
        phone=None,
        website="https://draft-electro.ru",
    )

    requirements = {
        "tender_summary": "Procurement of IEK electrical equipment in Moscow.",
        "technical_requirements": ["Electro equipment", "IEK components"],
        "qualification_requirements": [],
        "document_requirements": [],
        "evaluation_criteria": [],
        "procurement_categories": ["Electro"],
    }

    ranked = rank_suppliers_for_context(session, build_context_from_requirements(requirements), top_n=3)

    assert ranked[0].supplier.supplier_id == relevant.supplier_id
    assert ranked[0].source_type == "VENDOR_LIST"
    assert "score=" in ranked[0].inclusion_reason
    assert "category match" in ranked[0].inclusion_reason
    assert "brand match" in ranked[0].inclusion_reason
    assert "email available" in ranked[0].inclusion_reason
    assert "phone available" in ranked[0].inclusion_reason
    assert "website available" in ranked[0].inclusion_reason
    assert "source vendor-list" in ranked[0].inclusion_reason

    review_ranked = next(item for item in ranked if item.supplier.status == SupplierStatus.DRAFT)
    assert review_ranked.source_type == "VENDOR_LIST"
    assert "needs review" in review_ranked.inclusion_reason


def test_supplier_sourcing_snapshot_counts_distinct_vendor_list_suppliers(session):
    mixed_origin = _create_supplier(
        session,
        legal_name='АО "Кабель Реестр"',
        display_name="Кабель Реестр",
        inn="7703333333",
        status=SupplierStatus.ACTIVE,
        tags=[
            "CATEGORY_CABLE",
            "SOURCE_VENDOR_LIST",
            "SOURCE_VENDOR_LIST_ENRICHED",
            "REGION_MOSCOW",
        ],
        email="rfq@cable.ru",
        website="https://cable.ru",
    )
    pure_registry = _create_supplier(
        session,
        legal_name='ООО "Реестр Без Вендора"',
        display_name="Реестр Без Вендора",
        inn="7704444444",
        status=SupplierStatus.ACTIVE,
        tags=["CATEGORY_CABLE", "REGION_KAZAN"],
        email="registry@example.ru",
    )

    requirements = {
        "tender_summary": "Cable supply for Moscow site.",
        "technical_requirements": ["Cable drums", "power cable"],
        "qualification_requirements": [],
        "document_requirements": [],
        "evaluation_criteria": [],
        "procurement_categories": ["Cable"],
    }

    snapshot = get_supplier_sourcing_snapshot(session, requirements, top_n=5)

    assert snapshot["registry_supplier_count"] == 2
    assert snapshot["vendor_list_supplier_count"] == 1
    assert snapshot["top_suppliers"][0]["supplier_id"] == mixed_origin.supplier_id
    assert snapshot["top_suppliers"][0]["source_type"] == "REGISTRY_VENDOR_LIST"
    assert "score=" in snapshot["top_suppliers"][0]["inclusion_reason"]
    assert any(item["supplier_id"] == pure_registry.supplier_id for item in snapshot["top_suppliers"])
