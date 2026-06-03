from src.modules.deal_closure.models import DealArchiveSnapshot, DealClosureRecord, DealClosureSet
from src.modules.event_log.models import EventRecord
from src.modules.execution_command.models import ExecutionCommandSet
from src.modules.incidents.models import EscalationRecord, IncidentRecord, IncidentSet
from src.modules.kpi_learning.models import KPILearningRecord, KPILearningSet, LearningNoteRecord
from src.modules.payment_collection.models import PaymentCollectionSet
from src.modules.shipping_acceptance.models import ShippingAcceptanceSet
from src.modules.supplier_fulfillment.models import SupplierFulfillmentSet
from tests.test_sprint6a_integration import _prepare_awarded_outcome_context


def _prepare_completed_execution_context(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    deal_id = package["intake"]["deal_id"]
    launch = client.post(
        "/delivery-launch/build",
        json={"deal_id": deal_id, "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"]},
    ).json()
    client.post("/delivery-launch/launch", json={"delivery_launch_set_id": launch["delivery_launch_set_id"]})
    execution = client.post(
        "/execution/build",
        json={"deal_id": deal_id, "delivery_launch_set_id": launch["delivery_launch_set_id"]},
    ).json()
    fulfillment = client.post(
        "/supplier-fulfillment/build",
        json={"deal_id": deal_id, "execution_command_set_id": execution["execution_command_set_id"]},
    ).json()
    client.post(
        "/supplier-fulfillment/events",
        json={
            "supplier_fulfillment_id": fulfillment["records"][0]["supplier_fulfillment_id"],
            "summary": "Поставщик выполнил обязательства по заказу.",
            "fulfillment_state": "FULFILLED",
        },
    )
    shipping = client.post(
        "/shipping-acceptance/build",
        json={"deal_id": deal_id, "execution_command_set_id": execution["execution_command_set_id"]},
    ).json()
    client.post(
        "/shipping-acceptance/events",
        json={
            "shipping_acceptance_id": shipping["records"][0]["shipping_acceptance_id"],
            "summary": "Поставка и приемка завершены.",
            "current_state": "ACCEPTED",
            "shipment_ref": "SHIP-6B-001",
            "acceptance_ref": "ACT-6B-001",
        },
    )
    collection = client.post(
        "/payment-collection/build",
        json={"deal_id": deal_id, "execution_command_set_id": execution["execution_command_set_id"]},
    ).json()
    client.post(
        "/payment-collection/events",
        json={
            "payment_collection_id": collection["records"][0]["payment_collection_id"],
            "summary": "Счет выставлен клиенту.",
            "collection_state": "INVOICED",
            "invoice_ref": "INV-6B-001",
        },
    )
    client.post(
        "/payment-collection/events",
        json={
            "payment_collection_id": collection["records"][0]["payment_collection_id"],
            "summary": "Оплата получена в полном объеме.",
            "collection_state": "COLLECTED",
            "collected_amount": collection["records"][0]["expected_amount"],
        },
    )
    package["launch"] = launch
    package["execution"] = execution
    package["fulfillment"] = fulfillment
    package["shipping"] = shipping
    package["collection"] = collection
    return package


def _prepare_closed_deal_context(client, session):
    package = _prepare_completed_execution_context(client, session)
    closure = client.post(
        "/deal-closure/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
        },
    ).json()
    closed = client.post(
        "/deal-closure/close",
        json={
            "deal_closure_set_id": closure["deal_closure_set_id"],
            "summary_text": "Сделка завершена и закрыта после полной оплаты.",
        },
    ).json()
    package["closure"] = closed
    return package


def test_build_incident_set_and_persist_record(client, session):
    package = _prepare_completed_execution_context(client, session)
    response = client.post(
        "/incidents/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
        },
    )
    assert response.status_code == 201
    incident_set = response.json()
    record_response = client.post(
        "/incidents/register",
        json={
            "incident_set_id": incident_set["incident_set_id"],
            "incident_type": "DELIVERY",
            "severity": "HIGH",
            "summary": "Поставка сместилась на 2 дня.",
            "source_ref": package["shipping"]["records"][0]["shipping_acceptance_id"],
        },
    )
    assert record_response.status_code == 201
    record = record_response.json()

    persisted_set = session.query(IncidentSet).filter_by(incident_set_id=incident_set["incident_set_id"]).one()
    persisted_record = session.query(IncidentRecord).filter_by(incident_id=record["incident_id"]).one()

    assert persisted_set.deal_id == package["intake"]["deal_id"]
    assert persisted_record.incident_type == "DELIVERY"


def test_escalation_records_persisted_and_resolution_event_possible(client, session):
    package = _prepare_completed_execution_context(client, session)
    incident_set = client.post(
        "/incidents/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
        },
    ).json()
    record = client.post(
        "/incidents/register",
        json={
            "incident_set_id": incident_set["incident_set_id"],
            "incident_type": "PAYMENT",
            "severity": "MEDIUM",
            "summary": "Клиент запросил перенос срока оплаты.",
        },
    ).json()
    response = client.post(
        "/incidents/escalate",
        json={
            "incident_id": record["incident_id"],
            "escalation_level": "FINANCE",
            "escalation_status": "RESOLVED",
            "notes": "Финансы согласовали новый график.",
            "incident_status": "RESOLVED",
        },
    )
    assert response.status_code == 201

    escalation = session.query(EscalationRecord).filter_by(incident_id=record["incident_id"]).one()
    incident_db_set = session.query(IncidentSet).filter_by(incident_set_id=incident_set["incident_set_id"]).one()
    assert escalation.escalation_level == "FINANCE"
    assert incident_db_set.incident_status == "RESOLVED"


def test_build_deal_closure_and_archive_snapshot(client, session):
    package = _prepare_completed_execution_context(client, session)
    build = client.post(
        "/deal-closure/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
        },
    )
    assert build.status_code == 201
    closure = build.json()
    close = client.post(
        "/deal-closure/close",
        json={"deal_closure_set_id": closure["deal_closure_set_id"]},
    )
    assert close.status_code == 200
    payload = close.json()

    closure_set = session.query(DealClosureSet).filter_by(deal_closure_set_id=closure["deal_closure_set_id"]).one()
    closure_record = session.query(DealClosureRecord).filter_by(
        deal_closure_set_id=closure["deal_closure_set_id"]
    ).one()
    snapshot = session.query(DealArchiveSnapshot).filter_by(
        deal_closure_set_id=closure["deal_closure_set_id"]
    ).one()

    assert closure_set.closure_status == "CLOSED"
    assert closure_record.closure_code == "CLOSED_WON"
    assert snapshot.snapshot_manifest_json["execution_command_set_id"] == package["execution"]["execution_command_set_id"]
    assert len(payload["archive_snapshots"]) == 1


def test_build_kpi_snapshot_and_learning_notes(client, session):
    package = _prepare_closed_deal_context(client, session)
    response = client.post(
        "/kpi-learning/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "learning_notes": [
                {"note_type": "WHAT_WORKED", "note_text": "Раннее сравнение котировок ускорило выбор поставщика."},
                {"note_type": "PROCESS_GAP", "note_text": "Нужен более явный контроль receipt before award notice."},
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    kpi_set = session.query(KPILearningSet).filter_by(kpi_learning_set_id=payload["kpi_learning_set_id"]).one()
    kpi_record = session.query(KPILearningRecord).filter_by(kpi_learning_set_id=payload["kpi_learning_set_id"]).one()
    notes = session.query(LearningNoteRecord).filter_by(kpi_learning_id=kpi_record.kpi_learning_id).all()

    assert kpi_set.deal_id == package["intake"]["deal_id"]
    assert kpi_record.supplier_count >= 1
    assert len(notes) == 2


def test_sprint6b_outputs_linked_to_deal_and_events_written(client, session):
    package = _prepare_closed_deal_context(client, session)
    deal_id = package["intake"]["deal_id"]
    incident_set = client.post(
        "/incidents/build",
        json={"deal_id": deal_id, "execution_command_set_id": package["execution"]["execution_command_set_id"]},
    ).json()
    incident_record = client.post(
        "/incidents/register",
        json={
            "incident_set_id": incident_set["incident_set_id"],
            "incident_type": "COMMUNICATION",
            "severity": "LOW",
            "summary": "Потребовалось дополнительное согласование графика.",
        },
    ).json()
    client.post(
        "/incidents/escalate",
        json={
            "incident_id": incident_record["incident_id"],
            "escalation_level": "OWNER",
            "notes": "Зафиксировано для пост-анализа.",
        },
    )
    kpi = client.post(
        "/kpi-learning/build",
        json={
            "deal_id": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "learning_notes": [{"note_type": "CUSTOMER_LEARNING", "note_text": "Заказчик быстро принимает закрывающие документы."}],
        },
    ).json()

    assert session.query(IncidentSet).filter_by(incident_set_id=incident_set["incident_set_id"], deal_id=deal_id).count() == 1
    assert session.query(DealClosureSet).filter_by(
        deal_closure_set_id=package["closure"]["deal_closure_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(KPILearningSet).filter_by(
        kpi_learning_set_id=kpi["kpi_learning_set_id"], deal_id=deal_id
    ).count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "incident_set_built" in event_codes
    assert "incident_recorded" in event_codes
    assert "incident_escalated" in event_codes
    assert "deal_closure_built" in event_codes
    assert "deal_closed" in event_codes
    assert "deal_archive_snapshot_created" in event_codes
    assert "kpi_learning_built" in event_codes
    assert "learning_note_recorded" in event_codes


def test_outcome_prerequisite_enforced_for_closure(client, session):
    package = _prepare_completed_execution_context(client, session)
    response = client.post(
        "/deal-closure/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": "OIS-2099-999999",
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
        },
    )
    assert response.status_code == 404


def test_sprint6b_reruns_are_append_only(client, session):
    package = _prepare_closed_deal_context(client, session)
    deal_id = package["intake"]["deal_id"]
    first_incidents = client.post(
        "/incidents/build",
        json={"deal_id": deal_id, "execution_command_set_id": package["execution"]["execution_command_set_id"]},
    ).json()
    second_incidents = client.post(
        "/incidents/build",
        json={"deal_id": deal_id, "execution_command_set_id": package["execution"]["execution_command_set_id"]},
    ).json()
    assert first_incidents["incident_set_id"] != second_incidents["incident_set_id"]

    first_kpi = client.post(
        "/kpi-learning/build",
        json={"deal_id": deal_id, "deal_closure_set_id": package["closure"]["deal_closure_set_id"]},
    ).json()
    second_kpi = client.post(
        "/kpi-learning/build",
        json={"deal_id": deal_id, "deal_closure_set_id": package["closure"]["deal_closure_set_id"]},
    ).json()
    assert first_kpi["kpi_learning_set_id"] != second_kpi["kpi_learning_set_id"]
    assert session.query(IncidentSet).filter_by(deal_id=deal_id).count() == 2
    assert session.query(KPILearningSet).filter_by(deal_id=deal_id).count() == 2
