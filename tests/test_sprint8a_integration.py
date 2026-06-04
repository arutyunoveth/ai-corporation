from src.modules.action_queue.models import ActionQueueApproval, ActionQueueSet
from src.modules.connector_registry.models import ConnectorRegistrySet, ConnectorSyncRun
from src.modules.event_log.models import EventRecord
from src.modules.workspace_feed.models import WorkspaceFeedItem, WorkspaceFeedSet
from tests.test_sprint6b_integration import _prepare_closed_deal_context
from tests.test_sprint7b_integration import _prepare_optimization_context


def _prepare_control_context(client, session):
    package = _prepare_optimization_context(client, session)
    deal_id = package["intake"]["deal_id"]
    optimization = client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    copilot = client.post("/copilot-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    package["optimization"] = optimization
    package["copilot"] = copilot
    return package


def test_build_connector_registry(client, session):
    package = _prepare_control_context(client, session)
    response = client.post(
        "/connectors/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    registry_set = session.query(ConnectorRegistrySet).filter_by(
        connector_registry_set_id=payload["connector_registry_set_id"]
    ).one()
    assert registry_set.scope_ref == package["intake"]["deal_id"]


def test_connector_sync_run_persisted(client, session):
    package = _prepare_control_context(client, session)
    registry = client.post(
        "/connectors/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    connector_registry_id = registry["records"][0]["connector_registry_id"]

    response = client.post("/connectors/sync", json={"connector_registry_id": connector_registry_id})
    assert response.status_code == 201

    runs = session.query(ConnectorSyncRun).filter_by(connector_registry_id=connector_registry_id).all()
    assert len(runs) == 1


def test_build_workspace_feed(client, session):
    package = _prepare_control_context(client, session)
    response = client.post(
        "/workspace-feed/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    workspace_set = session.query(WorkspaceFeedSet).filter_by(
        workspace_feed_set_id=payload["workspace_feed_set_id"]
    ).one()
    assert workspace_set.scope_ref == package["intake"]["deal_id"]


def test_workspace_feed_items_persisted(client, session):
    package = _prepare_control_context(client, session)
    payload = client.post(
        "/workspace-feed/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    record = payload["records"][0]

    items = session.query(WorkspaceFeedItem).filter_by(workspace_feed_id=record["workspace_feed_id"]).all()
    assert len(items) >= 1


def test_build_action_queue(client, session):
    package = _prepare_control_context(client, session)
    client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    response = client.post(
        "/action-queue/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    queue_set = session.query(ActionQueueSet).filter_by(action_queue_set_id=payload["action_queue_set_id"]).one()
    assert queue_set.scope_ref == package["intake"]["deal_id"]


def test_action_queue_approvals_persisted(client, session):
    package = _prepare_control_context(client, session)
    client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    queue = client.post(
        "/action-queue/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    action_queue_id = queue["records"][0]["action_queue_id"]

    response = client.post(
        "/action-queue/approve",
        json={
            "action_queue_id": action_queue_id,
            "approval_status": "APPROVED",
            "approved_by_ref": "OWNER",
            "rationale": "Действие подтверждено оператором",
        },
    )
    assert response.status_code == 201

    approvals = session.query(ActionQueueApproval).filter_by(action_queue_id=action_queue_id).all()
    assert len(approvals) == 1


def test_sprint8a_outputs_linked_to_scope_and_deal(client, session):
    package = _prepare_control_context(client, session)
    deal_id = package["intake"]["deal_id"]

    connectors = client.post("/connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    workspace = client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    queue = client.post("/action-queue/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()

    assert session.query(ConnectorRegistrySet).filter_by(
        connector_registry_set_id=connectors["connector_registry_set_id"],
        scope_ref=deal_id,
    ).count() == 1
    assert session.query(WorkspaceFeedSet).filter_by(
        workspace_feed_set_id=workspace["workspace_feed_set_id"],
        scope_ref=deal_id,
    ).count() == 1
    assert session.query(ActionQueueSet).filter_by(
        action_queue_set_id=queue["action_queue_set_id"],
        scope_ref=deal_id,
    ).count() == 1


def test_sprint8a_key_events_written(client, session):
    package = _prepare_control_context(client, session)
    deal_id = package["intake"]["deal_id"]
    connectors = client.post("/connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    client.post("/connectors/sync", json={"connector_registry_id": connectors["records"][0]["connector_registry_id"]})
    client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    queue = client.post("/action-queue/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    client.post(
        "/action-queue/approve",
        json={
            "action_queue_id": queue["records"][0]["action_queue_id"],
            "approval_status": "APPROVED",
            "approved_by_ref": "OWNER",
            "rationale": "Действие подтверждено оператором",
        },
    )

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "connector_registry_built" in event_codes
    assert "connector_sync_started" in event_codes
    assert "connector_sync_finished" in event_codes
    assert "workspace_feed_built" in event_codes
    assert "workspace_feed_item_recorded" in event_codes
    assert "action_queue_built" in event_codes
    assert "action_queue_item_recorded" in event_codes
    assert "action_queue_approved" in event_codes


def test_workspace_feed_prerequisite_enforced(client, session):
    package = _prepare_closed_deal_context(client, session)
    response = client.post(
        "/workspace-feed/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 422


def test_action_queue_requires_workspace_feed_context(client, session):
    package = _prepare_control_context(client, session)
    response = client.post(
        "/action-queue/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 422


def test_sprint8a_reruns_are_append_only(client, session):
    package = _prepare_control_context(client, session)
    deal_id = package["intake"]["deal_id"]

    first_connectors = client.post("/connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_connectors = client.post("/connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_connectors["connector_registry_set_id"] != second_connectors["connector_registry_set_id"]

    first_workspace = client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_workspace = client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_workspace["workspace_feed_set_id"] != second_workspace["workspace_feed_set_id"]

    first_queue = client.post("/action-queue/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_queue = client.post("/action-queue/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_queue["action_queue_set_id"] != second_queue["action_queue_set_id"]

    assert session.query(ConnectorRegistrySet).filter_by(scope_ref=deal_id).count() >= 2
    assert session.query(WorkspaceFeedSet).filter_by(scope_ref=deal_id).count() >= 2
    assert session.query(ActionQueueSet).filter_by(scope_ref=deal_id).count() >= 2
