from src.modules.customer_registry.models import CustomerContour, CustomerExternalRef, CustomerProfile
from src.modules.deal_registry.models import Deal
from src.modules.document_ingestion.models import DocumentSet
from src.modules.event_log.models import EventRecord
from src.modules.intake_priority.models import IntakePriorityFactor, IntakePriorityRecord, IntakePrioritySet
from src.modules.requirement_extraction.models import (
    RequirementExtractionRecord,
    RequirementExtractionSet,
    RequirementSourceLink,
)
from src.modules.tender_import.models import TenderImportEvent, TenderImportPayload, TenderImportRun
from src.modules.tender_intake.models import TenderIntakeRecord
from src.modules.tender_normalization.models import (
    TenderNormalizationLink,
    TenderNormalizationRecord,
    TenderNormalizationSet,
)


def _create_customer(client, *, legal_name: str = "АО Тестовый заказчик", inn: str = "7700000000"):
    response = client.post(
        "/customers",
        json={
            "legal_name": legal_name,
            "inn": inn,
            "kpp": "770001001",
            "external_refs": [{"source_type": "EIS", "source_ref": "https://zakupki.example/customer"}],
            "contours": [{"contour_code": "B2G", "contour_name": "Госзакупки", "notes": "Основной закупочный контур"}],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_import_run(client):
    response = client.post(
        "/tender-import/runs",
        json={
            "source_type": "EIS",
            "source_ref": "https://zakupki.example/tender/123456789",
            "events": [
                {
                    "raw_procurement_number": "123456789",
                    "source_url": "https://zakupki.example/tender/123456789",
                    "payload_json": {
                        "source_type": "EIS",
                        "procurement_number": "123456789",
                        "title": "Поставка кабельной продукции",
                        "customer_name": "АО Тестовый заказчик",
                        "customer_inn": "7700000000",
                        "deadline_at": "2026-06-10T12:00:00+00:00",
                        "domain_type": "ELECTRICAL_EQUIPMENT",
                    },
                }
            ],
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_artifact(client, deal_id: str, file_name: str = "tz.pdf"):
    response = client.post(
        "/artifacts",
        json={
            "deal_id": deal_id,
            "artifact_type": "TENDER_DOC",
            "file_name": file_name,
            "mime_type": "application/pdf",
            "storage_uri": f"s3://bucket/{file_name}",
            "checksum_sha256": f"checksum-{file_name}",
        },
    )
    assert response.status_code == 201
    return response.json()


def _build_normalization(client, tender_import_event_id: str):
    response = client.post(
        "/tender-normalization/build",
        json={"tender_import_event_id": tender_import_event_id},
    )
    assert response.status_code == 201
    return response.json()


def test_customer_profile_create_read_update_and_query(client, session):
    created = _create_customer(client)

    customer = session.query(CustomerProfile).filter_by(customer_id=created["customer_id"]).one()
    refs = session.query(CustomerExternalRef).filter_by(customer_id=created["customer_id"]).all()
    contours = session.query(CustomerContour).filter_by(customer_id=created["customer_id"]).all()
    assert customer.legal_name == "АО Тестовый заказчик"
    assert any(item.source_type == "EIS" for item in refs)
    assert any(item.contour_code == "B2G" for item in contours)

    fetched = client.get(f"/customers/{created['customer_id']}")
    assert fetched.status_code == 200
    assert fetched.json()["inn"] == "7700000000"

    updated = client.patch(
        f"/customers/{created['customer_id']}",
        json={"customer_status": "ACTIVE", "legal_name": "АО Обновленный заказчик"},
    )
    assert updated.status_code == 200
    assert updated.json()["customer_status"] == "ACTIVE"

    listed = client.get("/customers", params={"q": "Обновленный", "inn": "7700000000"})
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert session.query(EventRecord).filter_by(event_code="customer_profile_created").count() == 1
    assert session.query(EventRecord).filter_by(event_code="customer_profile_updated").count() == 1


def test_tender_import_run_event_and_payload_persist(client, session):
    created = _create_import_run(client)

    run = session.query(TenderImportRun).filter_by(tender_import_run_id=created["tender_import_run_id"]).one()
    event = session.query(TenderImportEvent).filter_by(tender_import_run_id=run.tender_import_run_id).one()
    payload = session.query(TenderImportPayload).filter_by(tender_import_event_id=event.tender_import_event_id).one()
    assert run.run_status == "SUCCEEDED"
    assert event.raw_procurement_number == "123456789"
    assert payload.payload_json["title"] == "Поставка кабельной продукции"
    assert payload.payload_hash

    event_response = client.get(f"/tender-import/events/{event.tender_import_event_id}")
    assert event_response.status_code == 200
    assert event_response.json()["payload"]["payload_json"]["customer_name"] == "АО Тестовый заказчик"
    assert session.query(EventRecord).filter_by(event_code="tender_import_run_started").count() == 1
    assert session.query(EventRecord).filter_by(event_code="tender_import_event_recorded").count() == 1
    assert session.query(EventRecord).filter_by(event_code="tender_import_run_succeeded").count() == 1


def test_tender_normalization_build_links_customer_and_reuses_deal_on_rerun(client, session):
    import_run = _create_import_run(client)
    event_id = import_run["events"][0]["tender_import_event_id"]

    first = _build_normalization(client, event_id)
    second = _build_normalization(client, event_id)

    first_record = first["records"][0]
    second_record = second["records"][0]
    first_link = first_record["links"][0]
    second_link = second_record["links"][0]
    assert first_link["deal_id"] == second_link["deal_id"]
    assert first_link["customer_id"] == second_link["customer_id"]

    normalization_sets = session.query(TenderNormalizationSet).all()
    normalization_records = session.query(TenderNormalizationRecord).all()
    normalization_links = session.query(TenderNormalizationLink).all()
    deal = session.query(Deal).filter_by(deal_id=first_link["deal_id"]).one()
    intake = session.query(TenderIntakeRecord).filter_by(deal_id=deal.deal_id).first()
    customer = session.query(CustomerProfile).filter_by(customer_id=first_link["customer_id"]).one()
    assert len(normalization_sets) == 2
    assert len(normalization_records) == 2
    assert len(normalization_links) == 2
    assert deal.procurement_number == "123456789"
    assert intake is not None
    assert customer.legal_name == "АО Тестовый заказчик"
    assert session.query(EventRecord).filter_by(event_code="tender_normalization_built").count() == 2


def test_intake_priority_build_persists_factors_and_links_to_deal(client, session):
    import_run = _create_import_run(client)
    normalization = _build_normalization(client, import_run["events"][0]["tender_import_event_id"])
    deal_id = normalization["records"][0]["links"][0]["deal_id"]

    response = client.post("/intake-priority/build", json={"deal_id": deal_id})
    assert response.status_code == 201
    payload = response.json()

    priority_set = session.query(IntakePrioritySet).filter_by(intake_priority_set_id=payload["intake_priority_set_id"]).one()
    priority_record = session.query(IntakePriorityRecord).filter_by(intake_priority_set_id=priority_set.intake_priority_set_id).one()
    factors = session.query(IntakePriorityFactor).filter_by(intake_priority_id=priority_record.intake_priority_id).all()
    assert priority_set.deal_id == deal_id
    assert priority_record.priority_score > 0
    assert len(factors) == 5
    assert any(item.factor_code == "COMPLETENESS" for item in factors)

    listed = client.get("/intake-priority", params={"deal_id": deal_id})
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert session.query(EventRecord).filter_by(event_code="intake_priority_built").count() == 1


def test_requirement_extraction_build_persists_source_links_and_events(client, session):
    import_run = _create_import_run(client)
    normalization = _build_normalization(client, import_run["events"][0]["tender_import_event_id"])
    deal_id = normalization["records"][0]["links"][0]["deal_id"]
    intake = session.query(TenderIntakeRecord).filter_by(deal_id=deal_id).order_by(TenderIntakeRecord.created_at.desc()).first()
    assert intake is not None
    artifact = _create_artifact(client, deal_id, "technical_spec.pdf")
    document_set_response = client.post(
        "/document-ingestion/sets",
        json={
            "deal_id": deal_id,
            "intake_id": intake.intake_id,
            "set_type": "TENDER_INITIAL",
            "items": [
                {
                    "artifact_ref": artifact["artifact_ref"],
                    "item_role": "TZ",
                    "source_file_name": "technical_spec.pdf",
                    "sort_order": 1,
                }
            ],
        },
    )
    assert document_set_response.status_code == 201
    document_set_id = document_set_response.json()["document_set_id"]

    first = client.post("/requirements/extract", json={"document_set_id": document_set_id})
    second = client.post("/requirements/extract", json={"document_set_id": document_set_id})
    assert first.status_code == 201
    assert second.status_code == 201

    extraction = first.json()
    extraction_set = session.query(RequirementExtractionSet).filter_by(
        requirement_extraction_set_id=extraction["requirement_extraction_set_id"]
    ).one()
    records = session.query(RequirementExtractionRecord).filter_by(
        requirement_extraction_set_id=extraction_set.requirement_extraction_set_id
    ).all()
    links = session.query(RequirementSourceLink).all()
    document_set = session.query(DocumentSet).filter_by(document_set_id=document_set_id).one()
    assert extraction_set.document_set_id == document_set_id
    assert document_set.deal_id == deal_id
    assert len(records) == 1
    assert len(links) >= 1
    assert links[0].source_ref == artifact["artifact_ref"]
    assert session.query(RequirementExtractionSet).count() == 2
    assert session.query(EventRecord).filter_by(event_code="requirement_extraction_built").count() == 2
