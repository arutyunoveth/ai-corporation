from src.modules.bid_packages.models import BidPackageItem
from src.modules.delivery_launch.models import DeliveryLaunchFlag, DeliveryLaunchSet
from src.modules.delivery_milestones.models import DeliveryMilestoneEvent, DeliveryMilestoneRecord, DeliveryMilestoneSet
from src.modules.event_log.models import EventRecord
from src.modules.execution_command.models import ExecutionCommandBinding, ExecutionCommandRecord, ExecutionCommandSet
from src.modules.outcome_intake.models import OutcomeIntakeSet
from src.modules.payment_collection.models import PaymentCollectionEvent, PaymentCollectionRecord, PaymentCollectionSet
from src.modules.post_submission.models import PostSubmissionTrackerSet
from src.modules.shipping_acceptance.models import ShippingAcceptanceEvent, ShippingAcceptanceRecord, ShippingAcceptanceSet
from src.modules.supplier_fulfillment.models import (
    SupplierFulfillmentEvent,
    SupplierFulfillmentRecord,
    SupplierFulfillmentSet,
)
from tests.test_sprint5b_integration import _prepare_submitted_execution


def _prepare_awarded_outcome_context(client, session):
    package = _prepare_submitted_execution(client)
    tracker = client.post(
        "/post-submission/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
        },
    ).json()
    tracker_record = tracker["records"][0]
    client.post(
        "/post-submission/events",
        json={
            "post_submission_tracker_id": tracker_record["post_submission_tracker_id"],
            "event_type": "NOTICE",
            "summary": "Опубликован протокол с победой компании.",
            "stage": "AWARDED",
            "source_ref": "PROTO-AWARD-1",
        },
    )
    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    outcome = client.post(
        "/outcome-intake/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "post_submission_tracker_set_id": tracker["post_submission_tracker_set_id"],
            "outcome_code": "WON",
            "effective_at": "2026-06-15T09:00:00Z",
            "rationale": "Сделка выиграна по итогам рассмотрения.",
            "bindings": [{"artifact_ref": artifact_ref, "binding_type": "NOTICE"}],
        },
    ).json()
    package["tracker"] = tracker
    package["outcome"] = outcome
    return package


def test_build_delivery_launch_and_persist_flags(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    response = client.post(
        "/delivery-launch/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    launch_set = session.query(DeliveryLaunchSet).filter_by(
        delivery_launch_set_id=payload["delivery_launch_set_id"]
    ).one()
    record = payload["records"][0]
    flags = session.query(DeliveryLaunchFlag).filter_by(delivery_launch_id=record["delivery_launch_id"]).all()

    assert launch_set.deal_id == package["intake"]["deal_id"]
    assert record["launch_recommendation"] in {"READY", "BLOCKED", "NEEDS_REVIEW"}
    assert len(flags) >= 1


def test_awarded_outcome_prerequisite_enforced(client, session):
    package = _prepare_submitted_execution(client)
    tracker = client.post(
        "/post-submission/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
        },
    ).json()
    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    outcome = client.post(
        "/outcome-intake/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "post_submission_tracker_set_id": tracker["post_submission_tracker_set_id"],
            "outcome_code": "LOST",
            "effective_at": "2026-06-15T10:00:00Z",
            "rationale": "Проиграли по цене.",
            "bindings": [{"artifact_ref": artifact_ref, "binding_type": "PROTOCOL"}],
        },
    ).json()
    response = client.post(
        "/delivery-launch/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": outcome["outcome_intake_set_id"],
        },
    )
    assert response.status_code == 422


def test_build_execution_command_center(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    launch = client.post(
        "/delivery-launch/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"],
        },
    ).json()
    client.post(
        "/delivery-launch/launch",
        json={"delivery_launch_set_id": launch["delivery_launch_set_id"], "launched_by_ref": "OPS-LAUNCH"},
    )
    response = client.post(
        "/execution/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "delivery_launch_set_id": launch["delivery_launch_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    execution_set = session.query(ExecutionCommandSet).filter_by(
        execution_command_set_id=payload["execution_command_set_id"]
    ).one()
    bindings = session.query(ExecutionCommandBinding).filter_by(
        execution_command_set_id=payload["execution_command_set_id"]
    ).all()

    assert execution_set.deal_id == package["intake"]["deal_id"]
    assert len(bindings) >= 2
    assert payload["records"][0]["current_phase"] == "LAUNCHED"


def test_build_milestones_and_persist_events(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    launch = client.post(
        "/delivery-launch/build",
        json={"deal_id": package["intake"]["deal_id"], "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"]},
    ).json()
    client.post("/delivery-launch/launch", json={"delivery_launch_set_id": launch["delivery_launch_set_id"]})
    execution = client.post(
        "/execution/build",
        json={"deal_id": package["intake"]["deal_id"], "delivery_launch_set_id": launch["delivery_launch_set_id"]},
    ).json()
    response = client.post(
        "/delivery-milestones/build",
        json={"deal_id": package["intake"]["deal_id"], "execution_command_set_id": execution["execution_command_set_id"]},
    )
    assert response.status_code == 201
    milestone_set = response.json()
    procurement = next(item for item in milestone_set["records"] if item["milestone_code"] == "MS-PROCUREMENT")
    event = client.post(
        "/delivery-milestones/events",
        json={
            "delivery_milestone_id": procurement["delivery_milestone_id"],
            "summary": "Поставщик подтвердил запуск закупки.",
            "milestone_state": "IN_PROGRESS",
        },
    )
    assert event.status_code == 201

    persisted_set = session.query(DeliveryMilestoneSet).filter_by(
        delivery_milestone_set_id=milestone_set["delivery_milestone_set_id"]
    ).one()
    persisted_record = session.query(DeliveryMilestoneRecord).filter_by(
        delivery_milestone_id=procurement["delivery_milestone_id"]
    ).one()
    events = session.query(DeliveryMilestoneEvent).filter_by(
        delivery_milestone_id=procurement["delivery_milestone_id"]
    ).all()

    assert persisted_set.deal_id == package["intake"]["deal_id"]
    assert persisted_record.milestone_state == "IN_PROGRESS"
    assert len(events) == 1


def test_build_supplier_fulfillment_and_persist_events(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    launch = client.post(
        "/delivery-launch/build",
        json={"deal_id": package["intake"]["deal_id"], "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"]},
    ).json()
    client.post("/delivery-launch/launch", json={"delivery_launch_set_id": launch["delivery_launch_set_id"]})
    execution = client.post(
        "/execution/build",
        json={"deal_id": package["intake"]["deal_id"], "delivery_launch_set_id": launch["delivery_launch_set_id"]},
    ).json()
    response = client.post(
        "/supplier-fulfillment/build",
        json={"deal_id": package["intake"]["deal_id"], "execution_command_set_id": execution["execution_command_set_id"]},
    )
    assert response.status_code == 201
    fulfillment = response.json()
    record = fulfillment["records"][0]
    event = client.post(
        "/supplier-fulfillment/events",
        json={
            "supplier_fulfillment_id": record["supplier_fulfillment_id"],
            "summary": "Поставщик приступил к исполнению заказа.",
            "fulfillment_state": "IN_PROGRESS",
        },
    )
    assert event.status_code == 201

    fulfillment_set = session.query(SupplierFulfillmentSet).filter_by(
        supplier_fulfillment_set_id=fulfillment["supplier_fulfillment_set_id"]
    ).one()
    persisted_record = session.query(SupplierFulfillmentRecord).filter_by(
        supplier_fulfillment_id=record["supplier_fulfillment_id"]
    ).one()
    events = session.query(SupplierFulfillmentEvent).filter_by(
        supplier_fulfillment_id=record["supplier_fulfillment_id"]
    ).all()

    assert fulfillment_set.deal_id == package["intake"]["deal_id"]
    assert persisted_record.fulfillment_state == "IN_PROGRESS"
    assert len(events) == 1


def test_build_shipping_acceptance_and_persist_events(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    launch = client.post(
        "/delivery-launch/build",
        json={"deal_id": package["intake"]["deal_id"], "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"]},
    ).json()
    client.post("/delivery-launch/launch", json={"delivery_launch_set_id": launch["delivery_launch_set_id"]})
    execution = client.post(
        "/execution/build",
        json={"deal_id": package["intake"]["deal_id"], "delivery_launch_set_id": launch["delivery_launch_set_id"]},
    ).json()
    response = client.post(
        "/shipping-acceptance/build",
        json={"deal_id": package["intake"]["deal_id"], "execution_command_set_id": execution["execution_command_set_id"]},
    )
    assert response.status_code == 201
    shipping = response.json()
    record = shipping["records"][0]
    event = client.post(
        "/shipping-acceptance/events",
        json={
            "shipping_acceptance_id": record["shipping_acceptance_id"],
            "summary": "Товар принят заказчиком.",
            "current_state": "ACCEPTED",
            "shipment_ref": "SHIP-2026-001",
            "acceptance_ref": "ACT-2026-001",
        },
    )
    assert event.status_code == 201

    shipping_set = session.query(ShippingAcceptanceSet).filter_by(
        shipping_acceptance_set_id=shipping["shipping_acceptance_set_id"]
    ).one()
    persisted_record = session.query(ShippingAcceptanceRecord).filter_by(
        shipping_acceptance_id=record["shipping_acceptance_id"]
    ).one()
    events = session.query(ShippingAcceptanceEvent).filter_by(
        shipping_acceptance_id=record["shipping_acceptance_id"]
    ).all()

    assert shipping_set.shipping_status == "ACCEPTED"
    assert persisted_record.acceptance_ref == "ACT-2026-001"
    assert len(events) == 1


def test_build_payment_collection_and_persist_events(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    launch = client.post(
        "/delivery-launch/build",
        json={"deal_id": package["intake"]["deal_id"], "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"]},
    ).json()
    client.post("/delivery-launch/launch", json={"delivery_launch_set_id": launch["delivery_launch_set_id"]})
    execution = client.post(
        "/execution/build",
        json={"deal_id": package["intake"]["deal_id"], "delivery_launch_set_id": launch["delivery_launch_set_id"]},
    ).json()
    response = client.post(
        "/payment-collection/build",
        json={"deal_id": package["intake"]["deal_id"], "execution_command_set_id": execution["execution_command_set_id"]},
    )
    assert response.status_code == 201
    collection = response.json()
    record = collection["records"][0]
    event = client.post(
        "/payment-collection/events",
        json={
            "payment_collection_id": record["payment_collection_id"],
            "summary": "Счет выставлен клиенту.",
            "collection_state": "INVOICED",
            "invoice_ref": "INV-2026-001",
        },
    )
    assert event.status_code == 201

    collection_set = session.query(PaymentCollectionSet).filter_by(
        payment_collection_set_id=collection["payment_collection_set_id"]
    ).one()
    persisted_record = session.query(PaymentCollectionRecord).filter_by(
        payment_collection_id=record["payment_collection_id"]
    ).one()
    events = session.query(PaymentCollectionEvent).filter_by(
        payment_collection_id=record["payment_collection_id"]
    ).all()

    assert collection_set.collection_status == "INVOICED"
    assert persisted_record.invoice_ref == "INV-2026-001"
    assert len(events) == 1


def test_sprint6a_outputs_linked_to_deal_and_events_written(client, session):
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
    milestones = client.post(
        "/delivery-milestones/build",
        json={"deal_id": deal_id, "execution_command_set_id": execution["execution_command_set_id"]},
    ).json()
    fulfillment = client.post(
        "/supplier-fulfillment/build",
        json={"deal_id": deal_id, "execution_command_set_id": execution["execution_command_set_id"]},
    ).json()
    shipping = client.post(
        "/shipping-acceptance/build",
        json={"deal_id": deal_id, "execution_command_set_id": execution["execution_command_set_id"]},
    ).json()
    collection = client.post(
        "/payment-collection/build",
        json={"deal_id": deal_id, "execution_command_set_id": execution["execution_command_set_id"]},
    ).json()

    assert session.query(OutcomeIntakeSet).filter_by(
        outcome_intake_set_id=package["outcome"]["outcome_intake_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(PostSubmissionTrackerSet).filter_by(
        post_submission_tracker_set_id=package["tracker"]["post_submission_tracker_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(DeliveryLaunchSet).filter_by(
        delivery_launch_set_id=launch["delivery_launch_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(ExecutionCommandSet).filter_by(
        execution_command_set_id=execution["execution_command_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(DeliveryMilestoneSet).filter_by(
        delivery_milestone_set_id=milestones["delivery_milestone_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(SupplierFulfillmentSet).filter_by(
        supplier_fulfillment_set_id=fulfillment["supplier_fulfillment_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(ShippingAcceptanceSet).filter_by(
        shipping_acceptance_set_id=shipping["shipping_acceptance_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(PaymentCollectionSet).filter_by(
        payment_collection_set_id=collection["payment_collection_set_id"], deal_id=deal_id
    ).count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "delivery_launch_built" in event_codes
    assert "delivery_launch_started" in event_codes
    assert "execution_command_built" in event_codes
    assert "delivery_milestones_built" in event_codes
    assert "supplier_fulfillment_built" in event_codes
    assert "shipping_acceptance_built" in event_codes
    assert "payment_collection_built" in event_codes


def test_sprint6a_reruns_are_append_only(client, session):
    package = _prepare_awarded_outcome_context(client, session)
    deal_id = package["intake"]["deal_id"]
    first_launch = client.post(
        "/delivery-launch/build",
        json={"deal_id": deal_id, "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"]},
    ).json()
    second_launch = client.post(
        "/delivery-launch/build",
        json={"deal_id": deal_id, "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"]},
    ).json()
    assert first_launch["delivery_launch_set_id"] != second_launch["delivery_launch_set_id"]
    client.post("/delivery-launch/launch", json={"delivery_launch_set_id": first_launch["delivery_launch_set_id"]})
    first_execution = client.post(
        "/execution/build",
        json={"deal_id": deal_id, "delivery_launch_set_id": first_launch["delivery_launch_set_id"]},
    ).json()
    client.post("/delivery-launch/launch", json={"delivery_launch_set_id": second_launch["delivery_launch_set_id"]})
    second_execution = client.post(
        "/execution/build",
        json={"deal_id": deal_id, "delivery_launch_set_id": second_launch["delivery_launch_set_id"]},
    ).json()
    assert first_execution["execution_command_set_id"] != second_execution["execution_command_set_id"]
    assert session.query(DeliveryLaunchSet).filter_by(deal_id=deal_id).count() == 2
    assert session.query(ExecutionCommandSet).filter_by(deal_id=deal_id).count() == 2
