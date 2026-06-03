from src.modules.deal_registry.models import DealExternalRef
from src.modules.document_ingestion.models import DocumentIngestionRun, DocumentSet, DocumentSetItem
from src.modules.tender_intake.models import TenderIntakeRecord, TenderSourcePayload
from src.modules.tender_summary.models import TenderSummary, TenderSummarySourceLink


def _create_intake(client, procurement_number: str = "123456789", payload_json: dict | None = None):
    response = client.post(
        "/intake/tenders",
        json={
            "source_type": "MANUAL",
            "source_channel": "owner_manual_entry",
            "source_title": "Поставка автоматических выключателей",
            "source_customer_name": "АО Пример",
            "source_procurement_number": procurement_number,
            "payload_json": payload_json
            or {
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


def _create_artifact(client, deal_id: str, file_name: str = "notice.pdf"):
    response = client.post(
        "/artifacts",
        json={
            "deal_id": deal_id,
            "artifact_type": "TENDER_DOC",
            "file_name": file_name,
            "mime_type": "application/pdf",
            "storage_uri": f"s3://bucket/{file_name}",
            "checksum_sha256": f"hash-{file_name}",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_tender_intake_persists_record_and_payload(client, session):
    created = _create_intake(client)

    intake = session.query(TenderIntakeRecord).filter_by(intake_id=created["intake_id"]).one()
    payload = session.query(TenderSourcePayload).filter_by(intake_id=created["intake_id"]).one()
    assert intake.deal_id == created["deal_id"]
    assert intake.intake_status == "LINKED"
    assert payload.payload_json["portal_url"] == "https://example.com/tenders/123456789"
    assert session.query(DealExternalRef).filter_by(deal_id=created["deal_id"], ref_type="PORTAL_URL").count() == 1


def test_duplicate_intake_reuses_existing_deal(client):
    first = _create_intake(client)
    second = _create_intake(client)

    assert second["deal_id"] == first["deal_id"]
    assert second["duplicate_hint"] is True


def test_create_document_set_and_completed_ingestion_run(client, session):
    intake = _create_intake(client)
    first_artifact = _create_artifact(client, intake["deal_id"], "notice.pdf")
    second_artifact = _create_artifact(client, intake["deal_id"], "specification.pdf")

    create_response = client.post(
        "/document-ingestion/sets",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "set_type": "TENDER_INITIAL",
            "items": [
                {
                    "artifact_ref": first_artifact["artifact_ref"],
                    "item_role": "NOTICE",
                    "source_file_name": "notice.pdf",
                    "sort_order": 1,
                },
                {
                    "artifact_ref": second_artifact["artifact_ref"],
                    "item_role": "TZ",
                    "source_file_name": "specification.pdf",
                    "sort_order": 2,
                },
            ],
        },
    )
    assert create_response.status_code == 201
    created_document_set = create_response.json()
    assert created_document_set["ingestion_status"] == "CREATED"

    run_response = client.post(
        f"/document-ingestion/sets/{created_document_set['document_set_id']}/runs",
        json={"run_status": "COMPLETED", "notes": "Initial document ingestion complete"},
    )
    assert run_response.status_code == 201

    document_set = session.query(DocumentSet).filter_by(document_set_id=created_document_set["document_set_id"]).one()
    items = session.query(DocumentSetItem).filter_by(document_set_id=created_document_set["document_set_id"]).all()
    runs = session.query(DocumentIngestionRun).filter_by(document_set_id=created_document_set["document_set_id"]).all()
    assert document_set.ingestion_status == "INGESTED"
    assert len(items) == 2
    assert len(runs) == 1


def test_build_tender_summary_persists_links_and_structured_summary(client, session):
    intake = _create_intake(client)
    artifact = _create_artifact(client, intake["deal_id"], "notice.pdf")
    document_set = client.post(
        "/document-ingestion/sets",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "set_type": "TENDER_INITIAL",
            "items": [
                {
                    "artifact_ref": artifact["artifact_ref"],
                    "item_role": "NOTICE",
                    "source_file_name": "notice.pdf",
                    "sort_order": 1,
                }
            ],
        },
    ).json()

    summary_response = client.post(
        "/tender-summaries",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
        },
    )
    assert summary_response.status_code == 201
    summary_payload = summary_response.json()
    assert summary_payload["summary_status"] == "BUILT"

    summary = session.query(TenderSummary).filter_by(tender_summary_id=summary_payload["tender_summary_id"]).one()
    source_links = session.query(TenderSummarySourceLink).filter_by(tender_summary_id=summary.tender_summary_id).all()
    assert summary.structured_summary_json["document_count"] == 1
    assert summary.structured_summary_json["summary_version"] == "1.0"
    assert any(link.source_object_type == "DOCUMENT_SET" for link in source_links)
    assert any(link.source_object_type == "ARTIFACT" for link in source_links)


def test_query_intake_document_set_and_summary_by_deal(client):
    intake = _create_intake(client)
    artifact = _create_artifact(client, intake["deal_id"], "notice.pdf")
    document_set = client.post(
        "/document-ingestion/sets",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "set_type": "TENDER_INITIAL",
            "items": [
                {
                    "artifact_ref": artifact["artifact_ref"],
                    "item_role": "NOTICE",
                    "source_file_name": "notice.pdf",
                    "sort_order": 1,
                }
            ],
        },
    ).json()
    client.post(
        "/tender-summaries",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
        },
    )

    intake_response = client.get("/intake/tenders", params={"deal_id": intake["deal_id"]})
    document_sets_response = client.get("/document-ingestion/sets", params={"deal_id": intake["deal_id"]})
    summaries_response = client.get("/tender-summaries", params={"deal_id": intake["deal_id"]})

    assert intake_response.status_code == 200
    assert document_sets_response.status_code == 200
    assert summaries_response.status_code == 200
    assert len(intake_response.json()) == 1
    assert len(document_sets_response.json()) == 1
    assert len(summaries_response.json()) == 1
