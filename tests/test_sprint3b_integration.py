from src.modules.event_log.models import EventRecord
from src.modules.quote_comparison.models import (
    QuoteComparisonRecommendation,
    QuoteComparisonRow,
    QuoteComparisonSet,
)
from src.modules.supplier_verification.models import (
    SupplierVerificationFlag,
    SupplierVerificationRecord,
    SupplierVerificationSet,
)


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


def _prepare_supplier_package(client):
    intake, document_set, summary, matrix, requirements, risks = _build_analysis_package(client)

    first = _create_supplier(
        client, legal_name="ООО ЭлектроСнаб", display_name="ЭлектроСнаб", inn="7701234567"
    )
    second = _create_supplier(
        client, legal_name="ООО КабельИмпорт", display_name="КабельИмпорт", inn="7701234568"
    )

    client.post(
        f"/suppliers/{first['supplier_id']}/contacts",
        json={"contact_name": "Иван Петров", "email": "sales@electro.example", "is_primary": True},
    )
    client.post(f"/suppliers/{first['supplier_id']}/tags", json={"tag_code": "ELECTRICAL_EQUIPMENT"})
    client.post(f"/suppliers/{first['supplier_id']}/tags", json={"tag_code": "TENDER_READY"})
    client.post(
        f"/suppliers/{second['supplier_id']}/contacts",
        json={"contact_name": "Ольга Смирнова", "email": "quotes@cable.example", "is_primary": True},
    )

    shortlist = client.post(
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
    ).json()
    rfq_batch = client.post(
        "/rfq/batches/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()
    communication_set = client.post(
        "/supplier-communications/sets/build",
        json={"deal_id": intake["deal_id"], "rfq_batch_id": rfq_batch["rfq_batch_id"]},
    ).json()

    for thread in communication_set["threads"]:
        client.post(
            f"/supplier-communications/threads/{thread['supplier_thread_id']}/messages",
            json={
                "direction": "OUTBOUND",
                "message_subject": "Запрос ТКП",
                "message_text": "Просим направить коммерческое предложение.",
            },
        )

    for index, thread in enumerate(communication_set["threads"], start=1):
        quote_artifact = _create_artifact(
            client,
            intake["deal_id"],
            f"quote-{index}.pdf",
            artifact_type="SUPPLIER_QUOTE",
        )
        client.post(
            "/quotes/register",
            json={
                "deal_id": intake["deal_id"],
                "supplier_id": thread["supplier_id"],
                "rfq_id": thread["rfq_id"],
                "supplier_thread_id": thread["supplier_thread_id"],
                "quoted_amount": 120000.0 + index * 5000,
                "currency_code": "RUB",
                "notes": f"Quote {index}",
                "artifact_refs": [quote_artifact["artifact_ref"]],
            },
        )

    quote_list = client.get("/quotes", params={"deal_id": intake["deal_id"]}).json()
    quote_set_id = quote_list[0]["quote_set_id"]
    return intake, shortlist, rfq_batch, communication_set, quote_set_id


def test_build_verification_set_and_persist_records_flags(client, session):
    intake, shortlist, _rfq_batch, _communication_set, _quote_set_id = _prepare_supplier_package(client)

    response = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    verification_set = session.query(SupplierVerificationSet).filter_by(
        supplier_verification_set_id=payload["supplier_verification_set_id"]
    ).one()
    records = session.query(SupplierVerificationRecord).filter_by(
        supplier_verification_set_id=payload["supplier_verification_set_id"]
    ).all()
    flags = session.query(SupplierVerificationFlag).join(
        SupplierVerificationRecord,
        SupplierVerificationRecord.supplier_verification_id == SupplierVerificationFlag.supplier_verification_id,
    ).filter(SupplierVerificationRecord.supplier_verification_set_id == payload["supplier_verification_set_id"]).all()

    assert verification_set.deal_id == intake["deal_id"]
    assert len(records) >= 1
    assert len(flags) >= 1


def test_get_verification_record_and_query_by_deal(client):
    intake, shortlist, _rfq_batch, _communication_set, _quote_set_id = _prepare_supplier_package(client)
    verification_set = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()

    record_id = verification_set["records"][0]["supplier_verification_id"]
    record_response = client.get(f"/supplier-verification/records/{record_id}")
    list_response = client.get("/supplier-verification", params={"deal_id": intake["deal_id"]})

    assert record_response.status_code == 200
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_build_quote_comparison_and_persist_rows_recommendation(client, session):
    intake, shortlist, _rfq_batch, _communication_set, quote_set_id = _prepare_supplier_package(client)
    verification_set = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()

    response = client.post(
        "/quote-comparison/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_set_id": quote_set_id,
            "supplier_verification_set_id": verification_set["supplier_verification_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    comparison_set = session.query(QuoteComparisonSet).filter_by(
        quote_comparison_set_id=payload["quote_comparison_set_id"]
    ).one()
    rows = session.query(QuoteComparisonRow).filter_by(
        quote_comparison_set_id=payload["quote_comparison_set_id"]
    ).all()
    recommendation = session.query(QuoteComparisonRecommendation).filter_by(
        quote_comparison_set_id=payload["quote_comparison_set_id"]
    ).one()

    assert comparison_set.deal_id == intake["deal_id"]
    assert len(rows) >= 1
    assert recommendation.recommended_quote_id is not None


def test_get_comparison_recommendation_and_query_by_deal(client):
    intake, shortlist, _rfq_batch, _communication_set, quote_set_id = _prepare_supplier_package(client)
    verification_set = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()
    comparison_set = client.post(
        "/quote-comparison/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_set_id": quote_set_id,
            "supplier_verification_set_id": verification_set["supplier_verification_set_id"],
        },
    ).json()

    recommendation_response = client.get(
        f"/quote-comparison/recommendation/{comparison_set['quote_comparison_set_id']}"
    )
    list_response = client.get("/quote-comparison", params={"deal_id": intake["deal_id"]})

    assert recommendation_response.status_code == 200
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1


def test_sprint3b_outputs_linked_to_deal_and_key_events_written(client, session):
    intake, shortlist, _rfq_batch, _communication_set, quote_set_id = _prepare_supplier_package(client)
    verification_set = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()
    comparison_set = client.post(
        "/quote-comparison/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_set_id": quote_set_id,
            "supplier_verification_set_id": verification_set["supplier_verification_set_id"],
        },
    ).json()

    assert session.query(SupplierVerificationSet).filter_by(
        supplier_verification_set_id=verification_set["supplier_verification_set_id"],
        deal_id=intake["deal_id"],
    ).count() == 1
    assert session.query(QuoteComparisonSet).filter_by(
        quote_comparison_set_id=comparison_set["quote_comparison_set_id"],
        deal_id=intake["deal_id"],
    ).count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=intake["deal_id"]).all()}
    assert "supplier_verification_build_started" in event_codes
    assert "supplier_verification_built" in event_codes
    assert "quote_comparison_build_started" in event_codes
    assert "quote_comparison_built" in event_codes


def test_verification_and_comparison_reruns_are_append_only(client, session):
    intake, shortlist, _rfq_batch, _communication_set, quote_set_id = _prepare_supplier_package(client)
    first_verification = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()
    second_verification = client.post(
        "/supplier-verification/build",
        json={"deal_id": intake["deal_id"], "supplier_shortlist_id": shortlist["supplier_shortlist_id"]},
    ).json()

    assert first_verification["supplier_verification_set_id"] != second_verification["supplier_verification_set_id"]

    comparison_one = client.post(
        "/quote-comparison/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_set_id": quote_set_id,
            "supplier_verification_set_id": first_verification["supplier_verification_set_id"],
        },
    ).json()
    comparison_two = client.post(
        "/quote-comparison/build",
        json={
            "deal_id": intake["deal_id"],
            "quote_set_id": quote_set_id,
            "supplier_verification_set_id": second_verification["supplier_verification_set_id"],
        },
    ).json()

    assert comparison_one["quote_comparison_set_id"] != comparison_two["quote_comparison_set_id"]
    assert (
        session.query(QuoteComparisonSet).filter_by(deal_id=intake["deal_id"]).count() == 2
    )
