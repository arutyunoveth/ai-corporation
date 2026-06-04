from src.modules.action_console.models import ActionConsoleItem, ActionConsoleSet
from src.modules.event_log.models import EventRecord
from src.modules.execution_ledger.models import ExecutionLedgerSet
from src.modules.external_execution.models import (
    ExternalExecutionResult,
    ExternalExecutionSet,
)
from src.modules.integration_tasks.models import IntegrationTaskSet
from src.modules.operator_sessions.models import OperatorSessionSet
from src.modules.vendor_connectors.models import (
    VendorConnectorCapability,
    VendorConnectorRecord,
    VendorConnectorSet,
)
from tests.test_sprint8b_integration import _prepare_richer_control_context


def _prepare_sprint9a_context(client, session):
    package = _prepare_richer_control_context(client, session)
    deal_id = package["intake"]["deal_id"]
    integration = client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    operator = client.post(
        "/operator-sessions/build",
        json={"scope_type": "DEAL", "scope_ref": deal_id, "opened_by_ref": "OWNER"},
    ).json()
    ledger = client.post("/execution-ledger/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    vendor = client.post("/vendor-connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    package["integration"] = integration
    package["operator"] = operator
    package["ledger"] = ledger
    package["vendor"] = vendor
    return package


def test_build_vendor_connector_profiles(client, session):
    package = _prepare_richer_control_context(client, session)
    response = client.post(
        "/vendor-connectors/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()
    vendor_set = session.query(VendorConnectorSet).filter_by(
        vendor_connector_set_id=payload["vendor_connector_set_id"]
    ).one()
    assert vendor_set.scope_ref == package["intake"]["deal_id"]


def test_vendor_connector_capability_rows_persisted(client, session):
    package = _prepare_richer_control_context(client, session)
    payload = client.post(
        "/vendor-connectors/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    record = payload["records"][0]
    capabilities = session.query(VendorConnectorCapability).filter_by(
        vendor_connector_id=record["vendor_connector_id"]
    ).all()
    assert len(capabilities) >= 1


def test_build_action_console(client, session):
    package = _prepare_sprint9a_context(client, session)
    response = client.post(
        "/action-console/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()
    console_set = session.query(ActionConsoleSet).filter_by(
        action_console_set_id=payload["action_console_set_id"]
    ).one()
    assert console_set.scope_ref == package["intake"]["deal_id"]


def test_action_console_items_persisted(client, session):
    package = _prepare_sprint9a_context(client, session)
    payload = client.post(
        "/action-console/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    record = payload["records"][0]
    items = session.query(ActionConsoleItem).filter_by(action_console_id=record["action_console_id"]).all()
    assert len(items) >= 3


def test_build_external_execution_set(client, session):
    package = _prepare_sprint9a_context(client, session)
    response = client.post(
        "/external-execution/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()
    gateway_set = session.query(ExternalExecutionSet).filter_by(
        external_execution_set_id=payload["external_execution_set_id"]
    ).one()
    assert gateway_set.scope_ref == package["intake"]["deal_id"]


def test_external_execution_result_rows_persisted(client, session):
    package = _prepare_sprint9a_context(client, session)
    ledger_record = package["ledger"]["records"][0]
    client.post(
        "/execution-ledger/start",
        json={"execution_ledger_id": ledger_record["execution_ledger_id"], "executed_by_ref": "OWNER"},
    )
    gateway = client.post(
        "/external-execution/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    record = gateway["records"][0]
    response = client.post("/external-execution/start", json={"external_execution_id": record["external_execution_id"]})
    assert response.status_code == 201
    results = session.query(ExternalExecutionResult).filter_by(
        external_execution_id=record["external_execution_id"]
    ).all()
    assert len(results) == 1


def test_sprint9a_outputs_linked_to_scope_and_upstream_refs(client, session):
    package = _prepare_sprint9a_context(client, session)
    deal_id = package["intake"]["deal_id"]
    vendor = client.post("/vendor-connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    console = client.post("/action-console/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    gateway = client.post("/external-execution/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()

    assert session.query(VendorConnectorSet).filter_by(
        vendor_connector_set_id=vendor["vendor_connector_set_id"], scope_ref=deal_id
    ).count() == 1
    assert session.query(ActionConsoleSet).filter_by(
        action_console_set_id=console["action_console_set_id"], scope_ref=deal_id
    ).count() == 1
    assert session.query(ExternalExecutionSet).filter_by(
        external_execution_set_id=gateway["external_execution_set_id"], scope_ref=deal_id
    ).count() == 1

    external_record = gateway["records"][0]
    assert external_record["integration_task_id"]
    assert external_record["execution_ledger_id"]


def test_sprint9a_key_events_written(client, session):
    package = _prepare_sprint9a_context(client, session)
    deal_id = package["intake"]["deal_id"]
    client.post("/vendor-connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post("/action-console/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post(
        "/execution-ledger/start",
        json={"execution_ledger_id": package["ledger"]["records"][0]["execution_ledger_id"], "executed_by_ref": "OWNER"},
    )
    gateway = client.post("/external-execution/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    client.post("/external-execution/start", json={"external_execution_id": gateway["records"][0]["external_execution_id"]})

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "vendor_connector_profile_built" in event_codes
    assert "action_console_built" in event_codes
    assert "action_console_item_recorded" in event_codes
    assert "external_execution_built" in event_codes
    assert "external_execution_started" in event_codes
    assert "external_execution_succeeded" in event_codes or "external_execution_failed" in event_codes


def test_external_execution_requires_succeeded_internal_ledger(client, session):
    package = _prepare_sprint9a_context(client, session)
    gateway = client.post(
        "/external-execution/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    response = client.post(
        "/external-execution/start",
        json={"external_execution_id": gateway["records"][0]["external_execution_id"]},
    )
    assert response.status_code == 422


def test_sprint9a_reruns_are_append_only(client, session):
    package = _prepare_sprint9a_context(client, session)
    deal_id = package["intake"]["deal_id"]
    first_vendor = client.post("/vendor-connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_vendor = client.post("/vendor-connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_vendor["vendor_connector_set_id"] != second_vendor["vendor_connector_set_id"]

    first_console = client.post("/action-console/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_console = client.post("/action-console/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_console["action_console_set_id"] != second_console["action_console_set_id"]

    first_gateway = client.post("/external-execution/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_gateway = client.post("/external-execution/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_gateway["external_execution_set_id"] != second_gateway["external_execution_set_id"]
