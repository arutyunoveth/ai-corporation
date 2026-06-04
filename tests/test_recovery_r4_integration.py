from src.modules.claim_triggers.models import ClaimTriggerFlag, ClaimTriggerLink, ClaimTriggerRecord, ClaimTriggerSet
from src.modules.closing_docs.models import ClosingDocsFlag, ClosingDocsItem, ClosingDocsRecord, ClosingDocsSet
from src.modules.event_log.models import EventRecord
from src.modules.incident_register.models import (
    IncidentRegisterEvent,
    IncidentRegisterFlag,
    IncidentRegisterRecord,
    IncidentRegisterSet,
)
from src.modules.logistics_tracking.models import (
    LogisticsTrackingEvent,
    LogisticsTrackingLink,
    LogisticsTrackingRecord,
    LogisticsTrackingSet,
)
from src.modules.payment_tracking.models import (
    PaymentTrackingAlert,
    PaymentTrackingEvent,
    PaymentTrackingRecord,
    PaymentTrackingSet,
)
from src.modules.acceptance_control.models import (
    AcceptanceControlRecord,
    AcceptanceControlSet,
    AcceptanceRemark,
    AcceptanceResolutionItem,
)
from tests.test_recovery_r3_integration import _prepare_r3_progress_context


def _prepare_r4_logistics_context(client, session):
    package = _prepare_r3_progress_context(client, session)
    canonical_progress = client.post(
        "/supplier-progress/build",
        json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]},
    )
    assert canonical_progress.status_code == 201
    package["canonical_progress"] = canonical_progress.json()

    shipping = client.post(
        "/shipping-acceptance/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
            "shipment_ref": "SHIP-R4-001",
            "acceptance_ref": "ACC-R4-001",
        },
    )
    assert shipping.status_code == 201
    package["shipping"] = shipping.json()
    shipping_record = package["shipping"]["records"][0]
    shipping_event = client.post(
        "/shipping-acceptance/events",
        json={
            "shipping_acceptance_id": shipping_record["shipping_acceptance_id"],
            "summary": "Отгрузка вышла в путь.",
            "current_state": "SHIPPED",
        },
    )
    assert shipping_event.status_code == 201
    return package


def _prepare_r4_incident_context(client, session):
    package = _prepare_r4_logistics_context(client, session)
    logistics = client.post("/logistics-tracking/build", json={"deal_id": package["intake"]["deal_id"]})
    assert logistics.status_code == 201
    package["logistics"] = logistics.json()
    logistics_record = package["logistics"]["records"][0]
    assert (
        client.post(
            "/logistics-tracking/events",
            json={
                "logistics_tracking_id": logistics_record["logistics_tracking_id"],
                "event_type": "DELAY",
                "summary": "Перевозчик сообщил о задержке доставки.",
                "logistics_status": "DELAYED",
            },
        ).status_code
        == 201
    )
    return package


def _prepare_r4_acceptance_context(client, session):
    package = _prepare_r4_logistics_context(client, session)
    logistics = client.post("/logistics-tracking/build", json={"deal_id": package["intake"]["deal_id"]})
    assert logistics.status_code == 201
    package["logistics"] = logistics.json()
    logistics_record = package["logistics"]["records"][0]
    assert (
        client.post(
            "/logistics-tracking/events",
            json={
                "logistics_tracking_id": logistics_record["logistics_tracking_id"],
                "event_type": "DELIVERED",
                "summary": "Груз доставлен на площадку заказчика.",
                "logistics_status": "DELIVERED",
            },
        ).status_code
        == 201
    )
    shipping_record = package["shipping"]["records"][0]
    assert (
        client.post(
            "/shipping-acceptance/events",
            json={
                "shipping_acceptance_id": shipping_record["shipping_acceptance_id"],
                "summary": "Заказчик принял поставку.",
                "current_state": "ACCEPTED",
            },
        ).status_code
        == 201
    )
    return package


def _prepare_r4_closing_docs_context(client, session):
    package = _prepare_r4_acceptance_context(client, session)
    acceptance = client.post("/acceptance-control/build", json={"deal_id": package["intake"]["deal_id"]})
    assert acceptance.status_code == 201
    package["acceptance"] = acceptance.json()
    return package


def _prepare_r4_payment_context(client, session):
    package = _prepare_r4_closing_docs_context(client, session)
    closing_docs = client.post("/closing-docs/build", json={"deal_id": package["intake"]["deal_id"]})
    assert closing_docs.status_code == 201
    package["closing_docs"] = closing_docs.json()

    payment_helper = client.post(
        "/payment-collection/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
            "invoice_ref": "INV-R4-001",
            "expected_amount": 150000.0,
        },
    )
    assert payment_helper.status_code == 201
    package["payment_helper"] = payment_helper.json()
    return package


def test_build_logistics_tracking_and_persist_events_links(client, session):
    package = _prepare_r4_logistics_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="logistics_tracking_built").count()
    response = client.post("/logistics-tracking/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    tracking_set = session.query(LogisticsTrackingSet).filter_by(
        logistics_tracking_set_id=payload["logistics_tracking_set_id"]
    ).one()
    record = session.query(LogisticsTrackingRecord).filter_by(
        logistics_tracking_set_id=payload["logistics_tracking_set_id"]
    ).one()
    initial_events = session.query(LogisticsTrackingEvent).filter_by(
        logistics_tracking_id=record.logistics_tracking_id
    ).all()
    links = session.query(LogisticsTrackingLink).filter_by(logistics_tracking_id=record.logistics_tracking_id).all()

    assert tracking_set.deal_id == package["intake"]["deal_id"]
    assert len(initial_events) >= 1
    assert len(links) >= 2
    assert session.query(EventRecord).filter_by(event_code="logistics_tracking_built").count() == prior_event_count + 1

    prior_recorded_count = session.query(EventRecord).filter_by(event_code="logistics_tracking_event_recorded").count()
    event_response = client.post(
        "/logistics-tracking/events",
        json={
            "logistics_tracking_id": record.logistics_tracking_id,
            "event_type": "CHECKPOINT",
            "summary": "Машина прошла промежуточный checkpoint.",
            "source_ref": "TRACKING-CHECKPOINT-1",
        },
    )
    assert event_response.status_code == 201
    assert session.query(EventRecord).filter_by(event_code="logistics_tracking_event_recorded").count() == prior_recorded_count + 1


def test_build_incident_register_and_persist_events_flags(client, session):
    package = _prepare_r4_incident_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="incident_register_built").count()
    response = client.post("/incident-register/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    register_set = session.query(IncidentRegisterSet).filter_by(
        incident_register_set_id=payload["incident_register_set_id"]
    ).one()
    record = session.query(IncidentRegisterRecord).filter_by(
        incident_register_set_id=payload["incident_register_set_id"]
    ).one()
    events = session.query(IncidentRegisterEvent).filter_by(incident_register_id=record.incident_register_id).all()
    flags = session.query(IncidentRegisterFlag).filter_by(incident_register_id=record.incident_register_id).all()

    assert register_set.deal_id == package["intake"]["deal_id"]
    assert len(events) >= 1
    assert len(flags) >= 1
    assert session.query(EventRecord).filter_by(event_code="incident_register_built").count() == prior_event_count + 1

    prior_recorded_count = session.query(EventRecord).filter_by(event_code="incident_register_event_recorded").count()
    event_response = client.post(
        "/incident-register/events",
        json={
            "incident_register_id": record.incident_register_id,
            "event_type": "ESCALATED",
            "summary": "Инцидент эскалирован на владельца сделки.",
            "severity": "HIGH",
            "flag_code": "OWNER_ESCALATION",
        },
    )
    assert event_response.status_code == 201
    assert session.query(EventRecord).filter_by(event_code="incident_register_event_recorded").count() == prior_recorded_count + 1


def test_build_acceptance_control_and_persist_remarks_resolution(client, session):
    package = _prepare_r4_acceptance_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="acceptance_control_built").count()
    response = client.post("/acceptance-control/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    control_set = session.query(AcceptanceControlSet).filter_by(
        acceptance_control_set_id=payload["acceptance_control_set_id"]
    ).one()
    record = session.query(AcceptanceControlRecord).filter_by(
        acceptance_control_set_id=payload["acceptance_control_set_id"]
    ).one()
    remarks = session.query(AcceptanceRemark).filter_by(acceptance_control_id=record.acceptance_control_id).all()
    resolution_items = session.query(AcceptanceResolutionItem).filter_by(
        acceptance_control_id=record.acceptance_control_id
    ).all()

    assert control_set.deal_id == package["intake"]["deal_id"]
    assert len(remarks) >= 1
    assert len(resolution_items) >= 1
    assert session.query(EventRecord).filter_by(event_code="acceptance_control_built").count() == prior_event_count + 1


def test_build_closing_docs_and_persist_items_flags(client, session):
    package = _prepare_r4_closing_docs_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="closing_docs_built").count()
    response = client.post("/closing-docs/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    docs_set = session.query(ClosingDocsSet).filter_by(closing_docs_set_id=payload["closing_docs_set_id"]).one()
    record = session.query(ClosingDocsRecord).filter_by(closing_docs_set_id=payload["closing_docs_set_id"]).one()
    items = session.query(ClosingDocsItem).filter_by(closing_docs_id=record.closing_docs_id).all()
    flags = session.query(ClosingDocsFlag).filter_by(closing_docs_id=record.closing_docs_id).all()

    assert docs_set.deal_id == package["intake"]["deal_id"]
    assert len(items) >= 3
    assert len(flags) >= 1
    assert session.query(EventRecord).filter_by(event_code="closing_docs_built").count() == prior_event_count + 1


def test_build_payment_tracking_and_persist_events_alerts(client, session):
    package = _prepare_r4_payment_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="payment_tracking_built").count()
    response = client.post("/payment-tracking/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    tracking_set = session.query(PaymentTrackingSet).filter_by(
        payment_tracking_set_id=payload["payment_tracking_set_id"]
    ).one()
    record = session.query(PaymentTrackingRecord).filter_by(
        payment_tracking_set_id=payload["payment_tracking_set_id"]
    ).one()
    initial_events = session.query(PaymentTrackingEvent).filter_by(payment_tracking_id=record.payment_tracking_id).all()
    alerts = session.query(PaymentTrackingAlert).filter_by(payment_tracking_id=record.payment_tracking_id).all()

    assert tracking_set.deal_id == package["intake"]["deal_id"]
    assert len(initial_events) >= 1
    assert len(alerts) >= 1
    assert session.query(EventRecord).filter_by(event_code="payment_tracking_built").count() == prior_event_count + 1

    prior_recorded_count = session.query(EventRecord).filter_by(event_code="payment_tracking_event_recorded").count()
    event_response = client.post(
        "/payment-tracking/events",
        json={
            "payment_tracking_id": record.payment_tracking_id,
            "event_type": "OVERDUE",
            "summary": "Заказчик просрочил оплату.",
            "overdue_days": 12,
            "payment_status": "OVERDUE",
        },
    )
    assert event_response.status_code == 201
    assert session.query(EventRecord).filter_by(event_code="payment_tracking_event_recorded").count() == prior_recorded_count + 1


def test_build_claim_trigger_and_verify_query_linkage_and_reruns(client, session):
    package = _prepare_r4_payment_context(client, session)
    payment = client.post("/payment-tracking/build", json={"deal_id": package["intake"]["deal_id"]})
    assert payment.status_code == 201
    payment_record = payment.json()["records"][0]
    assert (
        client.post(
            "/payment-tracking/events",
            json={
                "payment_tracking_id": payment_record["payment_tracking_id"],
                "event_type": "OVERDUE",
                "summary": "Оплата просрочена, требуется претензионный контур.",
                "overdue_days": 15,
                "payment_status": "OVERDUE",
            },
        ).status_code
        == 201
    )

    base_claim_count = session.query(ClaimTriggerSet).filter_by(deal_id=package["intake"]["deal_id"]).count()
    response = client.post("/claim-triggers/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    trigger_set = session.query(ClaimTriggerSet).filter_by(claim_trigger_set_id=payload["claim_trigger_set_id"]).one()
    record = session.query(ClaimTriggerRecord).filter_by(claim_trigger_set_id=payload["claim_trigger_set_id"]).one()
    flags = session.query(ClaimTriggerFlag).filter_by(claim_trigger_id=record.claim_trigger_id).all()
    links = session.query(ClaimTriggerLink).filter_by(claim_trigger_id=record.claim_trigger_id).all()

    assert trigger_set.deal_id == package["intake"]["deal_id"]
    assert len(flags) >= 1
    assert len(links) >= 1
    assert session.query(EventRecord).filter_by(event_code="claim_trigger_built").count() >= 1

    rerun = client.post("/claim-triggers/build", json={"deal_id": package["intake"]["deal_id"]})
    assert rerun.status_code == 201
    listed = client.get("/claim-triggers", params={"deal_id": package["intake"]["deal_id"]})
    assert listed.status_code == 200
    assert session.query(ClaimTriggerSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == base_claim_count + 2
