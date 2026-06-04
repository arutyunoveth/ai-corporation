from src.modules.event_log.models import EventRecord
from src.modules.execution_plans.models import (
    ExecutionPlanAssumption,
    ExecutionPlanMilestone,
    ExecutionPlanRecord,
    ExecutionPlanSet,
)
from src.modules.purchase_orders.models import (
    PurchaseOrderItem,
    PurchaseOrderLink,
    PurchaseOrderRecord,
    PurchaseOrderSet,
)
from src.modules.supplier_contracts.models import (
    SupplierContractComment,
    SupplierContractObligation,
    SupplierContractRecord,
    SupplierContractSet,
)
from src.modules.supplier_progress.models import (
    SupplierProgressAlert,
    SupplierProgressEvent,
    SupplierProgressRecord,
    SupplierProgressSet,
)
from tests.test_recovery_r2_integration import _prepare_won_monitor_context


def _prepare_r3_contract_context(client, session):
    package = _prepare_won_monitor_context(client, session)
    negotiation = client.post(
        "/contract-negotiation/build",
        json={"deal_id": package["intake"]["deal_id"]},
    )
    assert negotiation.status_code == 201
    package["negotiation"] = negotiation.json()
    package["supplier_id"] = package["comparison"]["recommendation"]["recommended_supplier_id"]
    return package


def _prepare_r3_execution_plan_context(client, session):
    package = _prepare_r3_contract_context(client, session)
    supplier_contract = client.post(
        "/supplier-contracts/build",
        json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]},
    )
    assert supplier_contract.status_code == 201
    package["supplier_contract"] = supplier_contract.json()
    return package


def _prepare_r3_purchase_order_context(client, session):
    package = _prepare_r3_execution_plan_context(client, session)
    execution_plan = client.post("/execution-plans/build", json={"deal_id": package["intake"]["deal_id"]})
    assert execution_plan.status_code == 201
    package["execution_plan"] = execution_plan.json()
    return package


def _prepare_r3_progress_context(client, session):
    package = _prepare_r3_purchase_order_context(client, session)
    purchase_order = client.post(
        "/purchase-orders/build",
        json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]},
    )
    assert purchase_order.status_code == 201
    package["purchase_order"] = purchase_order.json()

    launch = client.post(
        "/delivery-launch/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"],
        },
    )
    assert launch.status_code == 201
    package["launch"] = launch.json()
    assert (
        client.post(
            "/delivery-launch/launch",
            json={"delivery_launch_set_id": package["launch"]["delivery_launch_set_id"], "launched_by_ref": "OPS-R3"},
        ).status_code
        == 200
    )
    execution = client.post(
        "/execution/build",
        json={"deal_id": package["intake"]["deal_id"], "delivery_launch_set_id": package["launch"]["delivery_launch_set_id"]},
    )
    assert execution.status_code == 201
    package["execution"] = execution.json()
    fulfillment = client.post(
        "/supplier-fulfillment/build",
        json={"deal_id": package["intake"]["deal_id"], "execution_command_set_id": package["execution"]["execution_command_set_id"]},
    )
    assert fulfillment.status_code == 201
    package["fulfillment"] = fulfillment.json()
    fulfillment_record = package["fulfillment"]["records"][0]
    assert (
        client.post(
            "/supplier-fulfillment/events",
            json={
                "supplier_fulfillment_id": fulfillment_record["supplier_fulfillment_id"],
                "summary": "Поставщик подтвердил переход в стадию сборки.",
                "fulfillment_state": "IN_PROGRESS",
            },
        ).status_code
        == 201
    )
    return package


def test_build_supplier_contract_and_persist_obligations_comments(client, session):
    package = _prepare_r3_contract_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="supplier_contract_built").count()
    response = client.post(
        "/supplier-contracts/build",
        json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    contract_set = session.query(SupplierContractSet).filter_by(
        supplier_contract_set_id=payload["supplier_contract_set_id"]
    ).one()
    record = session.query(SupplierContractRecord).filter_by(
        supplier_contract_set_id=payload["supplier_contract_set_id"]
    ).one()
    obligations = session.query(SupplierContractObligation).filter_by(
        supplier_contract_id=record.supplier_contract_id
    ).all()
    comments = session.query(SupplierContractComment).filter_by(
        supplier_contract_id=record.supplier_contract_id
    ).all()

    assert contract_set.deal_id == package["intake"]["deal_id"]
    assert contract_set.supplier_id == package["supplier_id"]
    assert len(obligations) >= 1
    assert len(comments) >= 1
    assert session.query(EventRecord).filter_by(event_code="supplier_contract_built").count() == prior_event_count + 1


def test_build_execution_plan_and_persist_milestones_assumptions(client, session):
    package = _prepare_r3_execution_plan_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="execution_plan_built").count()
    response = client.post("/execution-plans/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    plan_set = session.query(ExecutionPlanSet).filter_by(execution_plan_set_id=payload["execution_plan_set_id"]).one()
    record = session.query(ExecutionPlanRecord).filter_by(execution_plan_set_id=payload["execution_plan_set_id"]).one()
    milestones = session.query(ExecutionPlanMilestone).filter_by(execution_plan_id=record.execution_plan_id).all()
    assumptions = session.query(ExecutionPlanAssumption).filter_by(execution_plan_id=record.execution_plan_id).all()

    assert plan_set.deal_id == package["intake"]["deal_id"]
    assert len(milestones) >= 1
    assert len(assumptions) >= 1
    assert session.query(EventRecord).filter_by(event_code="execution_plan_built").count() == prior_event_count + 1


def test_build_purchase_order_and_persist_items_links(client, session):
    package = _prepare_r3_purchase_order_context(client, session)
    prior_event_count = session.query(EventRecord).filter_by(event_code="purchase_order_built").count()
    response = client.post(
        "/purchase-orders/build",
        json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    po_set = session.query(PurchaseOrderSet).filter_by(purchase_order_set_id=payload["purchase_order_set_id"]).one()
    record = session.query(PurchaseOrderRecord).filter_by(purchase_order_set_id=payload["purchase_order_set_id"]).one()
    items = session.query(PurchaseOrderItem).filter_by(purchase_order_id=record.purchase_order_id).all()
    links = session.query(PurchaseOrderLink).filter_by(purchase_order_id=record.purchase_order_id).all()

    assert po_set.deal_id == package["intake"]["deal_id"]
    assert po_set.supplier_id == package["supplier_id"]
    assert len(items) >= 1
    assert len(links) >= 1
    assert session.query(EventRecord).filter_by(event_code="purchase_order_built").count() == prior_event_count + 1


def test_build_supplier_progress_and_persist_events_alerts(client, session):
    package = _prepare_r3_progress_context(client, session)
    prior_build_event_count = session.query(EventRecord).filter_by(event_code="supplier_progress_built").count()
    response = client.post(
        "/supplier-progress/build",
        json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    progress_set = session.query(SupplierProgressSet).filter_by(
        supplier_progress_set_id=payload["supplier_progress_set_id"]
    ).one()
    record = session.query(SupplierProgressRecord).filter_by(
        supplier_progress_set_id=payload["supplier_progress_set_id"]
    ).one()
    initial_events = session.query(SupplierProgressEvent).filter_by(
        supplier_progress_id=record.supplier_progress_id
    ).all()

    assert progress_set.deal_id == package["intake"]["deal_id"]
    assert progress_set.supplier_id == package["supplier_id"]
    assert len(initial_events) >= 1
    assert session.query(EventRecord).filter_by(event_code="supplier_progress_built").count() == prior_build_event_count + 1

    prior_event_count = session.query(EventRecord).filter_by(event_code="supplier_progress_event_recorded").count()
    event_response = client.post(
        "/supplier-progress/events",
        json={
            "supplier_progress_id": record.supplier_progress_id,
            "event_type": "DELAY",
            "summary": "Поставщик сообщил о задержке по готовности.",
            "readiness_state": "DELAYED",
        },
    )
    assert event_response.status_code == 201
    alerts = session.query(SupplierProgressAlert).filter_by(supplier_progress_id=record.supplier_progress_id).all()

    assert any(alert.alert_code in {"SUPPLIER_DELAY", "MANUAL_PROGRESS_ALERT"} for alert in alerts)
    assert session.query(EventRecord).filter_by(event_code="supplier_progress_event_recorded").count() == prior_event_count + 1


def test_recovery_r3_outputs_query_by_deal_and_reruns_append_only(client, session):
    package = _prepare_r3_progress_context(client, session)
    base_contract_count = session.query(SupplierContractSet).filter_by(deal_id=package["intake"]["deal_id"]).count()
    base_plan_count = session.query(ExecutionPlanSet).filter_by(deal_id=package["intake"]["deal_id"]).count()
    base_order_count = session.query(PurchaseOrderSet).filter_by(deal_id=package["intake"]["deal_id"]).count()
    base_progress_count = session.query(SupplierProgressSet).filter_by(deal_id=package["intake"]["deal_id"]).count()

    client.post("/supplier-contracts/build", json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]})
    client.post("/supplier-contracts/build", json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]})
    client.post("/execution-plans/build", json={"deal_id": package["intake"]["deal_id"]})
    client.post("/execution-plans/build", json={"deal_id": package["intake"]["deal_id"]})
    client.post("/purchase-orders/build", json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]})
    client.post("/supplier-progress/build", json={"deal_id": package["intake"]["deal_id"], "supplier_id": package["supplier_id"]})

    contracts = client.get("/supplier-contracts", params={"deal_id": package["intake"]["deal_id"]})
    plans = client.get("/execution-plans", params={"deal_id": package["intake"]["deal_id"]})
    orders = client.get("/purchase-orders", params={"deal_id": package["intake"]["deal_id"]})
    progress = client.get("/supplier-progress", params={"deal_id": package["intake"]["deal_id"]})

    assert contracts.status_code == 200
    assert plans.status_code == 200
    assert orders.status_code == 200
    assert progress.status_code == 200
    assert session.query(SupplierContractSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == base_contract_count + 2
    assert session.query(ExecutionPlanSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == base_plan_count + 2
    assert session.query(PurchaseOrderSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == base_order_count + 1
    assert session.query(SupplierProgressSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == base_progress_count + 1
