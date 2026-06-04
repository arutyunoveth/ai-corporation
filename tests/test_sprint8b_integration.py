from src.modules.event_log.models import EventRecord
from src.modules.execution_ledger.models import ExecutionLedgerSet, ExecutionResultRecord
from src.modules.integration_tasks.models import IntegrationTaskBinding, IntegrationTaskSet
from src.modules.operator_sessions.models import OperatorSessionItem, OperatorSessionSet
from tests.test_sprint8a_integration import _prepare_control_context


def _prepare_richer_control_context(client, session):
    package = _prepare_control_context(client, session)
    deal_id = package["intake"]["deal_id"]
    connectors = client.post("/connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    queue = client.post("/action-queue/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    for record in queue["records"]:
        client.post(
            "/action-queue/approve",
            json={
                "action_queue_id": record["action_queue_id"],
                "approval_status": "APPROVED",
                "approved_by_ref": "OWNER",
                "rationale": "Оператор подтвердил controlled action",
            },
        )
    package["connectors"] = connectors
    package["queue"] = queue
    return package


def test_build_integration_task_set(client, session):
    package = _prepare_richer_control_context(client, session)
    response = client.post(
        "/integration-tasks/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()
    integration_set = session.query(IntegrationTaskSet).filter_by(
        integration_task_set_id=payload["integration_task_set_id"]
    ).one()
    assert integration_set.scope_ref == package["intake"]["deal_id"]


def test_integration_task_records_persisted(client, session):
    package = _prepare_richer_control_context(client, session)
    payload = client.post(
        "/integration-tasks/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    record = payload["records"][0]
    bindings = session.query(IntegrationTaskBinding).filter_by(
        integration_task_id=record["integration_task_id"]
    ).all()
    assert len(bindings) >= 2


def test_build_operator_sessions(client, session):
    package = _prepare_richer_control_context(client, session)
    client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    response = client.post(
        "/operator-sessions/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": package["intake"]["deal_id"],
            "opened_by_ref": "OWNER",
        },
    )
    assert response.status_code == 201
    payload = response.json()
    session_set = session.query(OperatorSessionSet).filter_by(
        operator_session_set_id=payload["operator_session_set_id"]
    ).one()
    assert session_set.scope_ref == package["intake"]["deal_id"]


def test_operator_session_items_persisted(client, session):
    package = _prepare_richer_control_context(client, session)
    client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    payload = client.post(
        "/operator-sessions/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": package["intake"]["deal_id"],
            "opened_by_ref": "OWNER",
        },
    ).json()
    record = payload["records"][0]
    items = session.query(OperatorSessionItem).filter_by(operator_session_id=record["operator_session_id"]).all()
    assert len(items) >= 1


def test_operator_session_acknowledge_persisted(client, session):
    package = _prepare_richer_control_context(client, session)
    client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    payload = client.post(
        "/operator-sessions/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": package["intake"]["deal_id"],
            "opened_by_ref": "OWNER",
        },
    ).json()
    record = payload["records"][0]
    item = record["items"][0]
    response = client.post(
        "/operator-sessions/items/ack",
        json={
            "operator_session_id": record["operator_session_id"],
            "item_code": item["item_code"],
            "source_ref": item["source_ref"],
        },
    )
    assert response.status_code == 201
    refreshed = session.query(OperatorSessionItem).filter_by(operator_session_id=record["operator_session_id"]).all()
    assert any(item.item_status == "ACKNOWLEDGED" for item in refreshed)


def test_build_execution_ledger(client, session):
    package = _prepare_richer_control_context(client, session)
    client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    response = client.post(
        "/execution-ledger/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()
    ledger_set = session.query(ExecutionLedgerSet).filter_by(
        execution_ledger_set_id=payload["execution_ledger_set_id"]
    ).one()
    assert ledger_set.scope_ref == package["intake"]["deal_id"]


def test_execution_result_records_persisted(client, session):
    package = _prepare_richer_control_context(client, session)
    client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    ledger = client.post(
        "/execution-ledger/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    record = ledger["records"][0]
    response = client.post(
        "/execution-ledger/start",
        json={"execution_ledger_id": record["execution_ledger_id"], "executed_by_ref": "OWNER"},
    )
    assert response.status_code == 201
    results = session.query(ExecutionResultRecord).filter_by(execution_ledger_id=record["execution_ledger_id"]).all()
    assert len(results) == 1


def test_sprint8b_outputs_linked_to_scope_and_upstream_refs(client, session):
    package = _prepare_richer_control_context(client, session)
    deal_id = package["intake"]["deal_id"]
    integration = client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    operator = client.post(
        "/operator-sessions/build",
        json={"scope_type": "DEAL", "scope_ref": deal_id, "opened_by_ref": "OWNER"},
    ).json()
    ledger = client.post("/execution-ledger/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()

    assert session.query(IntegrationTaskSet).filter_by(
        integration_task_set_id=integration["integration_task_set_id"], scope_ref=deal_id
    ).count() == 1
    assert session.query(OperatorSessionSet).filter_by(
        operator_session_set_id=operator["operator_session_set_id"], scope_ref=deal_id
    ).count() == 1
    assert session.query(ExecutionLedgerSet).filter_by(
        execution_ledger_set_id=ledger["execution_ledger_set_id"], scope_ref=deal_id
    ).count() == 1


def test_sprint8b_key_events_written(client, session):
    package = _prepare_richer_control_context(client, session)
    deal_id = package["intake"]["deal_id"]
    integration = client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    operator = client.post(
        "/operator-sessions/build",
        json={"scope_type": "DEAL", "scope_ref": deal_id, "opened_by_ref": "OWNER"},
    ).json()
    session_record = operator["records"][0]
    item = session_record["items"][0]
    client.post(
        "/operator-sessions/items/ack",
        json={
            "operator_session_id": session_record["operator_session_id"],
            "item_code": item["item_code"],
            "source_ref": item["source_ref"],
        },
    )
    ledger = client.post("/execution-ledger/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    client.post(
        "/execution-ledger/start",
        json={"execution_ledger_id": ledger["records"][0]["execution_ledger_id"], "executed_by_ref": "OWNER"},
    )

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "integration_task_built" in event_codes
    assert "operator_session_built" in event_codes
    assert "operator_session_item_recorded" in event_codes
    assert "operator_session_item_acknowledged" in event_codes
    assert "execution_ledger_built" in event_codes
    assert "execution_ledger_started" in event_codes
    assert "execution_ledger_succeeded" in event_codes or "execution_ledger_failed" in event_codes


def test_approval_prerequisite_enforced_for_execution_start(client, session):
    package = _prepare_control_context(client, session)
    deal_id = package["intake"]["deal_id"]
    client.post("/connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post("/action-queue/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    response = client.post("/execution-ledger/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert response.status_code == 422


def test_sprint8b_reruns_are_append_only(client, session):
    package = _prepare_richer_control_context(client, session)
    deal_id = package["intake"]["deal_id"]
    first_integration = client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_integration = client.post("/integration-tasks/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_integration["integration_task_set_id"] != second_integration["integration_task_set_id"]

    first_operator = client.post(
        "/operator-sessions/build",
        json={"scope_type": "DEAL", "scope_ref": deal_id, "opened_by_ref": "OWNER"},
    ).json()
    second_operator = client.post(
        "/operator-sessions/build",
        json={"scope_type": "DEAL", "scope_ref": deal_id, "opened_by_ref": "OWNER"},
    ).json()
    assert first_operator["operator_session_set_id"] != second_operator["operator_session_set_id"]

    first_ledger = client.post("/execution-ledger/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_ledger = client.post("/execution-ledger/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_ledger["execution_ledger_set_id"] != second_ledger["execution_ledger_set_id"]
