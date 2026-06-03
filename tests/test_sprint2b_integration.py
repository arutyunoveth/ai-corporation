from src.modules.compliance_matrix.models import ComplianceMatrix, ComplianceMatrixRow
from src.modules.document_requirements.models import DocumentRequirementRow, DocumentRequirementSet
from src.modules.event_log.models import EventRecord
from src.modules.initial_tech_risks.models import InitialTechRiskFlag, InitialTechRiskFlagSet
from src.modules.priority_scoring.models import PriorityScoreRecord
from src.modules.tender_screening.models import TenderScreeningRecord


def _create_intake(
    client,
    *,
    domain_type: str = "ELECTRICAL_EQUIPMENT",
    procurement_number: str | None = "123456789",
    payload_json: dict | None = None,
):
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
            "domain_type": domain_type,
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_artifact(client, deal_id: str, file_name: str, item_role: str = "TENDER_DOC"):
    response = client.post(
        "/artifacts",
        json={
            "deal_id": deal_id,
            "artifact_type": item_role,
            "file_name": file_name,
            "mime_type": "application/pdf",
            "storage_uri": f"s3://bucket/{file_name}",
            "checksum_sha256": f"hash-{file_name}",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_intake_package(
    client,
    *,
    domain_type: str = "ELECTRICAL_EQUIPMENT",
    procurement_number: str | None = "123456789",
    include_tz: bool = True,
    payload_json: dict | None = None,
):
    intake = _create_intake(
        client,
        domain_type=domain_type,
        procurement_number=procurement_number,
        payload_json=payload_json,
    )
    artifacts = [
        _create_artifact(client, intake["deal_id"], "notice.pdf"),
    ]
    items = [
        {
            "artifact_ref": artifacts[0]["artifact_ref"],
            "item_role": "NOTICE",
            "source_file_name": "notice.pdf",
            "sort_order": 1,
        }
    ]
    if include_tz:
        tz_artifact = _create_artifact(client, intake["deal_id"], "specification.pdf")
        artifacts.append(tz_artifact)
        items.append(
            {
                "artifact_ref": tz_artifact["artifact_ref"],
                "item_role": "TZ",
                "source_file_name": "specification.pdf",
                "sort_order": 2,
            }
        )
    document_set_response = client.post(
        "/document-ingestion/sets",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "set_type": "TENDER_INITIAL",
            "items": items,
        },
    )
    assert document_set_response.status_code == 201
    document_set = document_set_response.json()
    summary_response = client.post(
        "/tender-summaries",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
        },
    )
    assert summary_response.status_code == 201
    summary = summary_response.json()
    return intake, document_set, summary


def test_run_screening_on_valid_intake_package(client, session):
    intake, document_set, summary = _create_intake_package(client)
    response = client.post(
        "/screening/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    )
    assert response.status_code == 201
    screening = session.query(TenderScreeningRecord).filter_by(screening_id=response.json()["screening_id"]).one()
    assert screening.result_status == "PASS"
    assert screening.deal_id == intake["deal_id"]


def test_screening_fail_and_needs_review_paths(client):
    failing_intake, failing_document_set, failing_summary = _create_intake_package(client, domain_type="SERVICES")
    fail_response = client.post(
        "/screening/run",
        json={
            "deal_id": failing_intake["deal_id"],
            "intake_id": failing_intake["intake_id"],
            "document_set_id": failing_document_set["document_set_id"],
            "tender_summary_id": failing_summary["tender_summary_id"],
        },
    )
    assert fail_response.status_code == 201
    assert fail_response.json()["result_status"] == "FAIL"

    review_intake, review_document_set, review_summary = _create_intake_package(
        client,
        procurement_number=None,
        payload_json={
            "portal_url": "https://example.com/tenders/review-case",
            "notice_date": "2026-06-04",
        },
    )
    review_response = client.post(
        "/screening/run",
        json={
            "deal_id": review_intake["deal_id"],
            "intake_id": review_intake["intake_id"],
            "document_set_id": review_document_set["document_set_id"],
            "tender_summary_id": review_summary["tender_summary_id"],
        },
    )
    assert review_response.status_code == 201
    assert review_response.json()["result_status"] == "NEEDS_REVIEW"


def test_build_priority_score_and_persist_bucket(client, session):
    intake, document_set, summary = _create_intake_package(client)
    screening = client.post(
        "/screening/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    ).json()
    response = client.post(
        "/priority-scoring/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "screening_id": screening["screening_id"],
        },
    )
    assert response.status_code == 201
    record = session.query(PriorityScoreRecord).filter_by(priority_score_id=response.json()["priority_score_id"]).one()
    assert record.priority_bucket in {"HIGH", "MEDIUM", "LOW", "REJECT"}


def test_build_compliance_matrix_and_persist_rows(client, session):
    intake, document_set, summary = _create_intake_package(client)
    response = client.post(
        "/compliance-matrix/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    )
    assert response.status_code == 201
    matrix = session.query(ComplianceMatrix).filter_by(compliance_matrix_id=response.json()["compliance_matrix_id"]).one()
    rows = session.query(ComplianceMatrixRow).filter_by(compliance_matrix_id=matrix.compliance_matrix_id).all()
    assert matrix.matrix_row_count == len(rows)
    assert len(rows) >= 2


def test_extract_document_requirements_and_persist_rows(client, session):
    intake, document_set, summary = _create_intake_package(client)
    response = client.post(
        "/document-requirements/extract",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    )
    assert response.status_code == 201
    requirement_set = session.query(DocumentRequirementSet).filter_by(
        document_requirement_set_id=response.json()["document_requirement_set_id"]
    ).one()
    rows = session.query(DocumentRequirementRow).filter_by(
        document_requirement_set_id=requirement_set.document_requirement_set_id
    ).all()
    assert requirement_set.requirement_count == len(rows)
    assert len(rows) >= 1


def test_build_initial_tech_risk_flags_and_persist_severity_category(client, session):
    intake, document_set, summary = _create_intake_package(client, include_tz=False)
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
    response = client.post(
        "/initial-tech-risks/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "compliance_matrix_id": matrix["compliance_matrix_id"],
            "document_requirement_set_id": requirements["document_requirement_set_id"],
        },
    )
    assert response.status_code == 201
    flag_set = session.query(InitialTechRiskFlagSet).filter_by(risk_flag_set_id=response.json()["risk_flag_set_id"]).one()
    flags = session.query(InitialTechRiskFlag).filter_by(risk_flag_set_id=flag_set.risk_flag_set_id).all()
    assert flag_set.risk_flag_count == len(flags)
    assert all(flag.severity in {"LOW", "MEDIUM", "HIGH", "CRITICAL"} for flag in flags)
    assert all(flag.risk_category in {"AMBIGUITY", "INCOMPLETE_SPEC", "BRAND_LOCK", "EQUIVALENCE_RISK", "TIMELINE_RISK", "OTHER"} for flag in flags)


def test_all_sprint2b_records_linked_to_deal_and_key_events_written(client, session):
    intake, document_set, summary = _create_intake_package(client, include_tz=False)
    screening = client.post(
        "/screening/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    ).json()
    priority = client.post(
        "/priority-scoring/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "screening_id": screening["screening_id"],
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

    assert session.query(TenderScreeningRecord).filter_by(screening_id=screening["screening_id"], deal_id=intake["deal_id"]).count() == 1
    assert session.query(PriorityScoreRecord).filter_by(priority_score_id=priority["priority_score_id"], deal_id=intake["deal_id"]).count() == 1
    assert session.query(ComplianceMatrix).filter_by(compliance_matrix_id=matrix["compliance_matrix_id"], deal_id=intake["deal_id"]).count() == 1
    assert session.query(DocumentRequirementSet).filter_by(document_requirement_set_id=requirements["document_requirement_set_id"], deal_id=intake["deal_id"]).count() == 1
    assert session.query(InitialTechRiskFlagSet).filter_by(risk_flag_set_id=risks["risk_flag_set_id"], deal_id=intake["deal_id"]).count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=intake["deal_id"]).all()}
    assert "tender_screening_started" in event_codes
    assert "tender_screening_completed" in event_codes
    assert "priority_scoring_completed" in event_codes
    assert "compliance_matrix_built" in event_codes
    assert "document_requirements_extracted" in event_codes
    assert "initial_tech_risk_built" in event_codes


def test_query_sprint2b_records_by_deal(client):
    intake, document_set, summary = _create_intake_package(client, include_tz=False)
    screening = client.post(
        "/screening/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    ).json()
    client.post(
        "/priority-scoring/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "screening_id": screening["screening_id"],
        },
    )
    client.post(
        "/compliance-matrix/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    )
    client.post(
        "/document-requirements/extract",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    )
    client.post(
        "/initial-tech-risks/build",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "compliance_matrix_id": client.get("/compliance-matrix", params={"deal_id": intake["deal_id"]}).json()[0][
                "compliance_matrix_id"
            ],
            "document_requirement_set_id": client.get(
                "/document-requirements", params={"deal_id": intake["deal_id"]}
            ).json()[0]["document_requirement_set_id"],
        },
    )

    assert client.get("/screening", params={"deal_id": intake["deal_id"]}).status_code == 200
    assert len(client.get("/screening", params={"deal_id": intake["deal_id"]}).json()) == 1
    assert len(client.get("/priority-scoring", params={"deal_id": intake["deal_id"]}).json()) == 1
    assert len(client.get("/compliance-matrix", params={"deal_id": intake["deal_id"]}).json()) == 1
    assert len(client.get("/document-requirements", params={"deal_id": intake["deal_id"]}).json()) == 1
    assert len(client.get("/initial-tech-risks", params={"deal_id": intake["deal_id"]}).json()) == 1


def test_missing_prerequisite_path_and_source_trace_preservation(client, session):
    intake, document_set, summary = _create_intake_package(client)
    missing_prereq = client.post(
        "/priority-scoring/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
            "screening_id": "SCR-2099-999999",
        },
    )
    assert missing_prereq.status_code == 404

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
    stored_flags = session.query(InitialTechRiskFlag).filter_by(risk_flag_set_id=risks["risk_flag_set_id"]).all()
    assert any(flag.source_ref for flag in stored_flags)


def test_screening_rerun_creates_distinct_records(client, session):
    intake, document_set, summary = _create_intake_package(client)
    first = client.post(
        "/screening/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    ).json()
    second = client.post(
        "/screening/run",
        json={
            "deal_id": intake["deal_id"],
            "intake_id": intake["intake_id"],
            "document_set_id": document_set["document_set_id"],
            "tender_summary_id": summary["tender_summary_id"],
        },
    ).json()

    assert first["screening_id"] != second["screening_id"]
    assert (
        session.query(TenderScreeningRecord)
        .filter_by(deal_id=intake["deal_id"], intake_id=intake["intake_id"], document_set_id=document_set["document_set_id"])
        .count()
        == 2
    )
