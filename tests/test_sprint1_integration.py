from src.modules.deal_registry.models import Deal
from src.modules.document_store.models import ArtifactLink, ArtifactVersion, DocumentArtifact
from src.modules.event_log.models import DecisionRecord, EventRecord
from src.modules.status_engine.models import DealStatusHistory, StatusTransitionRule
from src.modules.status_engine.service import seed_default_rules


def _create_deal(client):
    response = client.post(
        "/deals",
        json={
            "title": "Поставка автоматических выключателей",
            "customer_name": "АО Пример",
            "procurement_number": "123456789",
            "procurement_channel": "ETP",
            "initial_source_type": "portal_ingest",
            "direction_type": "SUPPLY",
            "domain_type": "ELECTRICAL_EQUIPMENT",
        },
    )
    assert response.status_code == 201
    return response.json()


def _create_artifact(client, deal_id: str):
    response = client.post(
        "/artifacts",
        json={
            "deal_id": deal_id,
            "artifact_type": "TENDER_DOC",
            "file_name": "specification.pdf",
            "mime_type": "application/pdf",
            "storage_uri": "s3://bucket/specification.pdf",
            "checksum_sha256": "abc123",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_create_deal(client, session):
    payload = _create_deal(client)
    stored = session.query(Deal).filter_by(deal_id=payload["deal_id"]).one()
    assert stored.title == "Поставка автоматических выключателей"
    assert stored.current_status == "NEW"


def test_unique_deal_id_generation(client):
    first = _create_deal(client)
    second = _create_deal(client)
    assert first["deal_id"] != second["deal_id"]


def test_valid_status_transition(client, session):
    seed_default_rules(session)
    deal = _create_deal(client)
    response = client.post(
        "/status/apply-transition",
        json={
            "deal_id": deal["deal_id"],
            "to_status": "CANDIDATE",
            "changed_by_type": "SYSTEM",
            "changed_by_ref": "M-051",
            "reason_code": "intake_completed",
            "reason_text": "Deal moved into candidate after intake",
            "is_override": False,
        },
    )
    assert response.status_code == 200
    assert response.json()["to_status"] == "CANDIDATE"


def test_invalid_status_transition_blocked(client, session):
    seed_default_rules(session)
    deal = _create_deal(client)
    response = client.post(
        "/status/apply-transition",
        json={
            "deal_id": deal["deal_id"],
            "to_status": "SUBMISSION",
            "changed_by_type": "SYSTEM",
            "changed_by_ref": "M-051",
        },
    )
    assert response.status_code == 422


def test_status_history_append_only(client, session):
    seed_default_rules(session)
    deal = _create_deal(client)
    client.post(
        "/status/apply-transition",
        json={"deal_id": deal["deal_id"], "to_status": "CANDIDATE", "changed_by_type": "SYSTEM"},
    )
    client.post(
        "/status/apply-transition",
        json={"deal_id": deal["deal_id"], "to_status": "DOCS_ANALYSIS", "changed_by_type": "SYSTEM"},
    )
    history_rows = session.query(DealStatusHistory).filter_by(deal_id=deal["deal_id"]).all()
    assert len(history_rows) == 3


def test_create_artifact(client):
    deal = _create_deal(client)
    artifact = _create_artifact(client, deal["deal_id"])
    assert artifact["artifact_ref"].startswith("ART-")
    assert artifact["current_version"] == 1


def test_add_artifact_version(client, session):
    deal = _create_deal(client)
    artifact = _create_artifact(client, deal["deal_id"])
    response = client.post(
        f"/artifacts/{artifact['artifact_ref']}/versions",
        json={"storage_uri": "s3://bucket/specification_v2.pdf", "checksum_sha256": "def456"},
    )
    assert response.status_code == 201
    versions = session.query(ArtifactVersion).filter_by(artifact_ref=artifact["artifact_ref"]).all()
    assert len(versions) == 2


def test_link_artifact_to_deal(client, session):
    deal = _create_deal(client)
    artifact = _create_artifact(client, deal["deal_id"])
    response = client.post(
        f"/artifacts/{artifact['artifact_ref']}/links",
        json={"linked_object_type": "DEAL", "linked_object_ref": deal["deal_id"]},
    )
    assert response.status_code == 201
    link = session.query(ArtifactLink).filter_by(artifact_ref=artifact["artifact_ref"]).one()
    assert link.linked_object_ref == deal["deal_id"]


def test_append_event(client, session):
    deal = _create_deal(client)
    response = client.post(
        "/events",
        json={
            "deal_id": deal["deal_id"],
            "event_code": "deal_metadata_updated",
            "source_module_id": "M-001",
            "severity": "INFO",
            "payload_json": {"field": "customer_name"},
        },
    )
    assert response.status_code == 201
    assert session.query(EventRecord).count() >= 2


def test_append_decision(client, session):
    deal = _create_deal(client)
    response = client.post(
        "/decisions",
        json={
            "deal_id": deal["deal_id"],
            "decision_code": "MANUAL_STATUS_OVERRIDE",
            "decided_by_type": "HUMAN",
            "decided_by_ref": "CEO",
            "rationale": "Manual correction",
            "payload_json": {"from_status": "NEW", "to_status": "CANDIDATE"},
        },
    )
    assert response.status_code == 201
    assert session.query(DecisionRecord).count() == 1


def test_query_events_by_deal(client):
    deal = _create_deal(client)
    client.post(
        "/events",
        json={
            "deal_id": deal["deal_id"],
            "event_code": "deal_metadata_updated",
            "source_module_id": "M-001",
            "severity": "INFO",
        },
    )
    response = client.get("/events", params={"deal_id": deal["deal_id"]})
    assert response.status_code == 200
    assert all(item["deal_id"] == deal["deal_id"] for item in response.json())


def test_query_decisions_by_deal(client):
    deal = _create_deal(client)
    client.post(
        "/decisions",
        json={
            "deal_id": deal["deal_id"],
            "decision_code": "MANUAL_STATUS_OVERRIDE",
            "decided_by_type": "HUMAN",
            "decided_by_ref": "CEO",
            "rationale": "Manual override required for review",
        },
    )
    response = client.get("/decisions", params={"deal_id": deal["deal_id"]})
    assert response.status_code == 200
    assert all(item["deal_id"] == deal["deal_id"] for item in response.json())


def test_current_status_syncs_with_latest_history(client, session):
    seed_default_rules(session)
    deal = _create_deal(client)
    client.post(
        "/status/apply-transition",
        json={"deal_id": deal["deal_id"], "to_status": "CANDIDATE", "changed_by_type": "SYSTEM"},
    )
    stored_deal = session.query(Deal).filter_by(deal_id=deal["deal_id"]).one()
    latest = (
        session.query(DealStatusHistory)
        .filter_by(deal_id=deal["deal_id"])
        .order_by(DealStatusHistory.created_at.desc(), DealStatusHistory.id.desc())
        .first()
    )
    assert latest is not None
    assert stored_deal.current_status == latest.to_status
