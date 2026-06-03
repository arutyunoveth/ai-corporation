from src.modules.event_log.models import EventRecord
from src.modules.quote_repository.models import QuoteRecord, QuoteSet
from src.modules.rfq_generator.models import RFQBatch, RFQRecord
from src.modules.supplier_communications.models import (
    SupplierCommunicationSet,
    SupplierCommunicationThread,
    SupplierMessageRecord,
)
from src.modules.supplier_registry.models import SupplierContact, SupplierProfile, SupplierTag
from src.modules.supplier_search.models import SupplierShortlist, SupplierShortlistRow


def _create_intake(client):
    response = client.post(
        "/intake/tenders",
        json={
            "source_type": "MANUAL",
            "source_channel": "owner_manual_entry",
            "source_title": "Поставка автоматических выключателей",
            "source_customer_name": "АО Пример",
            "source_procurement_number": "123456789",
            "payload_json": {
                "portal_url": "https://example.com/tenders/123456789",
                "notice_date": "2026-06-03",
            },
            "initial_source_type": "manual_entry",
            "direction_type": "SUPPLY",
            "domain_type": "ELECTRICAL_EQUIPMENT",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_artifact(client, deal_id: str, file_name: str, artifact_type: str = "TENDER_DOC"):
    response = client.post(
        "/artifacts",
        json={
            "deal_id": deal_id,
            "artifact_type": artifact_type,
            "file_name": file_name,
            "mime_type": "application/pdf",
            "storage_uri": f"s3://bucket/{file_name}",
            "checksum_sha256": f"hash-{file_name}",
        },
    )
    assert response.status_code == 201
    return response.json()


def _build_analysis_package(client):
    intake = _create_intake(client)
    notice = _create_artifact(client, intake["deal_id"], "notice.pdf")
    specification = _create_artifact(client, intake["deal_id"], "specification.pdf")
    document_set = client.post(
        "/document-ingestion/sets",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "set_type": "TENDER_INITIAL",
            "items": [
                {
                    "artifact_ref": notice["artifact_ref"],
                    "item_role": "NOTICE",
                    "source_file_name": "notice.pdf",
                    "sort_order": 1,
                },
                {
                    "artifact_ref": specification["artifact_ref"],
                    "item_role": "TZ",
                    "source_file_name": "specification.pdf",
                    "sort_order": 2,
                },
            ],
        },
    ).json()
    summary = client.post(
        "/tender-summaries",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
        },
    ).json()
    matrix = client.post(
        "/compliance-matrix/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    ).json()
    requirements = client.post(
        "/document-requirements/extract",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    ).json()
    risks = client.post(
        "/initial-tech-risks/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "compliance_matrix_id": matrix["compliance_matrix_id"],
            "document_requirement_set_id": requirements["document_requirement_set_id"],
        },
    ).json()
    return intake, document_set, summary, matrix, requirements, risks


def _create_supplier(client, *, legal_name: str, display_name: str, inn: str):
    response = client.post(
        "/suppliers",
        json={
            "legal_name": legal_name,
            "display_name": display_name,
            "inn": inn,
            "country_code": "RU",
            "status": "ACTIVE",
        },
    )
    assert response.status_code == 201
    return response.json()


def _prepare_suppliers(client):
    first = _create_supplier(
        client,
        legal_name="ООО ЭлектроСнаб",
        display_name="ЭлектроСнаб",
        inn="7701234567",
    )
    second = _create_supplier(
        client,
        legal_name="ООО КабельИмпорт",
        display_name="КабельИмпорт",
        inn="7701234568",
    )
    client.post(
        f"/suppliers/{first['supplier_id']}/contacts",
        json={"contact_name": "Иван Петров", "email": "sales@electro.example", "is_primary": True},
    )
    client.post(f"/suppliers/{first['supplier_id']}/tags", json={"tag_code": "ELECTRICAL_EQUIPMENT"})
    client.post(f"/suppliers/{first['supplier_id']}/tags", json={"tag_code": "TENDER_READY"})
    client.post(f"/suppliers/{second['supplier_id']}/tags", json={"tag_code": "IMPORTED"})
    return first, second


def _build_shortlist(client, intake, document_set, summary, matrix, requirements, risks):
    response = client.post(
        "/supplier-search/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "compliance_matrix_id": matrix["compliance_matrix_id"],
            "document_requirement_set_id": requirements["document_requirement_set_id"],
            "risk_flag_set_id": risks["risk_flag_set_id"],
        },
    )
    assert response.status_code == 201
    return response.json()


def _build_rfq_batch(client, deal_id: str, supplier_shortlist_id: str):
    response = client.post(
        "/rfq/batches/build",
        json={"deal_id": deal_id, "supplier_shortlist_id": supplier_shortlist_id},
    )
    assert response.status_code == 201
    return response.json()


def _build_communication_set(client, deal_id: str, rfq_batch_id: str):
    response = client.post(
        "/supplier-communications/sets/build",
        json={"deal_id": deal_id, "rfq_batch_id": rfq_batch_id},
    )
    assert response.status_code == 201
    return response.json()


def test_create_supplier_profile_and_unique_supplier_ids(client, session):
    first = _create_supplier(client, legal_name="ООО ЭлектроСнаб", display_name="ЭлектроСнаб", inn="7701234567")
    second = _create_supplier(client, legal_name="ООО КабельИмпорт", display_name="КабельИмпорт", inn="7701234568")
    stored = session.query(SupplierProfile).filter_by(supplier_id=first["supplier_id"]).one()
    assert stored.inn == "7701234567"
    assert first["supplier_id"] != second["supplier_id"]


def test_duplicate_supplier_handling_by_inn(client):
    first = _create_supplier(client, legal_name="ООО ЭлектроСнаб", display_name="ЭлектроСнаб", inn="7701234567")
    duplicate = _create_supplier(client, legal_name="ООО ЭлектроСнаб 2", display_name="ЭлектроСнаб 2", inn="7701234567")
    assert duplicate["supplier_id"] == first["supplier_id"]
    assert duplicate["duplicate_hint"] is True


def test_build_shortlist_from_analysis_package_and_persist_rows(client, session):
    intake, document_set, summary, matrix, requirements, risks = _build_analysis_package(client)
    _prepare_suppliers(client)
    shortlist = _build_shortlist(client, intake, document_set, summary, matrix, requirements, risks)

    stored_shortlist = session.query(SupplierShortlist).filter_by(
        supplier_shortlist_id=shortlist["supplier_shortlist_id"]
    ).one()
    rows = session.query(SupplierShortlistRow).filter_by(
        supplier_shortlist_id=shortlist["supplier_shortlist_id"]
    ).all()
    assert stored_shortlist.deal_id == intake["deal_id"]
    assert len(rows) >= 1


def test_build_rfq_batch_and_persist_records(client, session):
    intake, document_set, summary, matrix, requirements, risks = _build_analysis_package(client)
    _prepare_suppliers(client)
    shortlist = _build_shortlist(client, intake, document_set, summary, matrix, requirements, risks)
    batch = _build_rfq_batch(client, intake["deal_id"], shortlist["supplier_shortlist_id"])

    stored_batch = session.query(RFQBatch).filter_by(rfq_batch_id=batch["rfq_batch_id"]).one()
    records = session.query(RFQRecord).filter_by(rfq_batch_id=batch["rfq_batch_id"]).all()
    assert stored_batch.deal_id == intake["deal_id"]
    assert len(records) == len(batch["rfq_records"])


def test_create_communication_set_threads_and_record_messages(client, session):
    intake, document_set, summary, matrix, requirements, risks = _build_analysis_package(client)
    _prepare_suppliers(client)
    shortlist = _build_shortlist(client, intake, document_set, summary, matrix, requirements, risks)
    batch = _build_rfq_batch(client, intake["deal_id"], shortlist["supplier_shortlist_id"])
    communication_set = _build_communication_set(client, intake["deal_id"], batch["rfq_batch_id"])
    thread_id = communication_set["threads"][0]["supplier_thread_id"]

    outbound = client.post(
        f"/supplier-communications/threads/{thread_id}/messages",
        json={
            "direction": "OUTBOUND",
            "message_subject": "Запрос ТКП",
            "message_text": "Просим направить коммерческое предложение.",
        },
    )
    inbound = client.post(
        f"/supplier-communications/threads/{thread_id}/messages",
        json={
            "direction": "INBOUND",
            "message_subject": "Re: Запрос ТКП",
            "message_text": "Подготовим предложение и направим.",
        },
    )

    assert outbound.status_code == 201
    assert inbound.status_code == 201
    stored_set = session.query(SupplierCommunicationSet).filter_by(
        supplier_communication_set_id=communication_set["supplier_communication_set_id"]
    ).one()
    threads = session.query(SupplierCommunicationThread).filter_by(
        supplier_communication_set_id=communication_set["supplier_communication_set_id"]
    ).all()
    messages = session.query(SupplierMessageRecord).filter_by(supplier_thread_id=thread_id).all()
    assert stored_set.deal_id == intake["deal_id"]
    assert len(threads) == len(batch["rfq_records"])
    assert len(messages) == 2


def test_register_quote_links_supplier_rfq_thread_and_revision_path(client, session):
    intake, document_set, summary, matrix, requirements, risks = _build_analysis_package(client)
    suppliers = _prepare_suppliers(client)
    shortlist = _build_shortlist(client, intake, document_set, summary, matrix, requirements, risks)
    batch = _build_rfq_batch(client, intake["deal_id"], shortlist["supplier_shortlist_id"])
    communication_set = _build_communication_set(client, intake["deal_id"], batch["rfq_batch_id"])
    thread = communication_set["threads"][0]
    supplier_id = thread["supplier_id"]
    rfq_id = thread["rfq_id"]
    client.post(
        f"/supplier-communications/threads/{thread['supplier_thread_id']}/messages",
        json={
            "direction": "OUTBOUND",
            "message_subject": "Запрос ТКП",
            "message_text": "Просим направить коммерческое предложение.",
        },
    )
    quote_artifact_v1 = _create_artifact(client, intake["deal_id"], "quote-v1.pdf", artifact_type="SUPPLIER_QUOTE")
    quote_v1 = client.post(
        "/quotes/register",
        json={
            "deal_id": intake["deal_id"],
            "supplier_id": supplier_id,
            "rfq_id": rfq_id,
            "supplier_thread_id": thread["supplier_thread_id"],
            "quoted_amount": 125000.0,
            "currency_code": "RUB",
            "notes": "Первичная ТКП",
            "artifact_refs": [quote_artifact_v1["artifact_ref"]],
        },
    )
    quote_artifact_v2 = _create_artifact(client, intake["deal_id"], "quote-v2.pdf", artifact_type="SUPPLIER_QUOTE")
    quote_v2 = client.post(
        "/quotes/register",
        json={
            "deal_id": intake["deal_id"],
            "supplier_id": supplier_id,
            "rfq_id": rfq_id,
            "supplier_thread_id": thread["supplier_thread_id"],
            "quoted_amount": 120000.0,
            "currency_code": "RUB",
            "notes": "Уточненная ТКП",
            "artifact_refs": [quote_artifact_v2["artifact_ref"]],
        },
    )

    assert quote_v1.status_code == 201
    assert quote_v2.status_code == 201
    stored_quote = session.query(QuoteRecord).filter_by(quote_id=quote_v1.json()["quote_id"]).one()
    revised_quote = session.query(QuoteRecord).filter_by(quote_id=quote_v2.json()["quote_id"]).one()
    quote_set = session.query(QuoteSet).filter_by(quote_set_id=stored_quote.quote_set_id).one()
    assert stored_quote.supplier_id == supplier_id
    assert stored_quote.rfq_id == rfq_id
    assert stored_quote.supplier_thread_id == thread["supplier_thread_id"]
    assert revised_quote.quote_status == "REVISED"
    assert quote_set.deal_id == intake["deal_id"]
    assert suppliers[0]["supplier_id"] == supplier_id


def test_all_supplier_side_outputs_linked_to_deal_and_events_written(client, session):
    intake, document_set, summary, matrix, requirements, risks = _build_analysis_package(client)
    _prepare_suppliers(client)
    shortlist = _build_shortlist(client, intake, document_set, summary, matrix, requirements, risks)
    batch = _build_rfq_batch(client, intake["deal_id"], shortlist["supplier_shortlist_id"])
    communication_set = _build_communication_set(client, intake["deal_id"], batch["rfq_batch_id"])
    thread = communication_set["threads"][0]
    client.post(
        f"/supplier-communications/threads/{thread['supplier_thread_id']}/messages",
        json={
            "direction": "OUTBOUND",
            "message_subject": "Запрос ТКП",
            "message_text": "Просим направить коммерческое предложение.",
        },
    )
    quote_artifact = _create_artifact(client, intake["deal_id"], "quote-final.pdf", artifact_type="SUPPLIER_QUOTE")
    client.post(
        "/quotes/register",
        json={
            "deal_id": intake["deal_id"],
            "supplier_id": thread["supplier_id"],
            "rfq_id": thread["rfq_id"],
            "supplier_thread_id": thread["supplier_thread_id"],
            "quoted_amount": 130000.0,
            "currency_code": "RUB",
            "artifact_refs": [quote_artifact["artifact_ref"]],
        },
    )

    assert client.get("/supplier-search", params={"deal_id": intake["deal_id"]}).status_code == 200
    assert len(client.get("/supplier-search", params={"deal_id": intake["deal_id"]}).json()) == 1
    assert len(client.get("/rfq/batches", params={"deal_id": intake["deal_id"]}).json()) == 1
    assert len(client.get("/supplier-communications/sets", params={"deal_id": intake["deal_id"]}).json()) == 1
    assert len(client.get("/quotes", params={"deal_id": intake["deal_id"]}).json()) >= 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=intake["deal_id"]).all()}
    assert "supplier_shortlist_built" in event_codes
    assert "rfq_batch_built" in event_codes
    assert "supplier_communication_set_created" in event_codes
    assert "supplier_message_recorded" in event_codes
    assert "quote_registered" in event_codes


def test_supplier_registry_contacts_and_tags_persist(client, session):
    supplier = _create_supplier(client, legal_name="ООО ЭлектроСнаб", display_name="ЭлектроСнаб", inn="7701234567")
    client.post(
        f"/suppliers/{supplier['supplier_id']}/contacts",
        json={"contact_name": "Иван Петров", "email": "sales@electro.example", "is_primary": True},
    )
    client.post(f"/suppliers/{supplier['supplier_id']}/tags", json={"tag_code": "ELECTRICAL_EQUIPMENT"})

    assert session.query(SupplierContact).filter_by(supplier_id=supplier["supplier_id"]).count() == 1
    assert session.query(SupplierTag).filter_by(supplier_id=supplier["supplier_id"]).count() == 1
