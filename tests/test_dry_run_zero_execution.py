from src.modules.action_queue.models import ActionQueueApproval, ActionQueueSet
from src.modules.event_log.models import EventRecord
from src.modules.launch_visibility.models import LaunchVisibilityItem, LaunchVisibilityRecord, LaunchVisibilitySet
from src.modules.workspace_feed.models import WorkspaceFeedItem, WorkspaceFeedSet
from tests.test_recovery_r5_integration import _prepare_r5_final_context


def _execute_dry_run_zero(client, session):
    package = _prepare_r5_final_context(client, session)
    deal_id = package["intake"]["deal_id"]

    report = client.post("/deal-closure-reports/build", json={"deal_id": deal_id})
    assert report.status_code == 201
    package["deal_closure_report"] = report.json()

    postmortem = client.post("/postmortems/build", json={"deal_id": deal_id})
    assert postmortem.status_code == 201
    package["postmortem"] = postmortem.json()

    rating = client.post("/supplier-ratings/build", json={"deal_id": deal_id})
    assert rating.status_code == 201
    package["supplier_rating"] = rating.json()

    knowledge = client.post("/knowledge-assets/build", json={"deal_id": deal_id})
    assert knowledge.status_code == 201
    package["knowledge_asset"] = knowledge.json()

    dashboard = client.post("/dashboards/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert dashboard.status_code == 201
    package["dashboard_refresh"] = dashboard.json()

    learning = client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    )
    assert learning.status_code == 201
    package["learning"] = learning.json()

    workflow = client.post("/workflow-runs/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert workflow.status_code == 201
    package["workflow"] = workflow.json()

    optimization = client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert optimization.status_code == 201
    package["optimization"] = optimization.json()

    copilot = client.post("/copilot-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert copilot.status_code == 201
    package["copilot"] = copilot.json()

    connectors = client.post("/connectors/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert connectors.status_code == 201
    package["connectors"] = connectors.json()

    connector_registry_id = package["connectors"]["records"][0]["connector_registry_id"]
    connector_sync = client.post("/connectors/sync", json={"connector_registry_id": connector_registry_id})
    assert connector_sync.status_code == 201
    package["connector_sync"] = connector_sync.json()

    workspace = client.post("/workspace-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert workspace.status_code == 201
    package["workspace"] = workspace.json()

    action_queue = client.post("/action-queue/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert action_queue.status_code == 201
    package["action_queue"] = action_queue.json()

    action_queue_id = package["action_queue"]["records"][0]["action_queue_id"]
    approval = client.post(
        "/action-queue/approve",
        json={
            "action_queue_id": action_queue_id,
            "approval_status": "APPROVED",
            "approved_by_ref": "DRY_RUN_OPERATOR",
            "rationale": "Dry Run 0 manual control gate approved the surfaced action.",
        },
    )
    assert approval.status_code == 201
    package["action_queue_approval"] = approval.json()

    visibility = client.post("/launch-visibility/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert visibility.status_code == 201
    package["launch_visibility"] = visibility.json()

    pilot_visibility = client.post("/launch-visibility/build", json={"scope_type": "PILOT", "scope_ref": "DRY-RUN-0"})
    assert pilot_visibility.status_code == 201
    package["pilot_visibility"] = pilot_visibility.json()

    return package


def test_dry_run_zero_rehearsal_executes_end_to_end(client, session):
    package = _execute_dry_run_zero(client, session)
    deal_id = package["intake"]["deal_id"]

    assert package["comparison"]["quote_comparison_set_id"]
    assert package["supplier_contract"]["supplier_contract_set_id"]
    assert package["execution_plan"]["execution_plan_set_id"]
    assert package["purchase_order"]["purchase_order_set_id"]
    assert package["logistics"]["logistics_tracking_set_id"]
    assert package["incident_register"]["incident_register_set_id"]
    assert package["acceptance"]["acceptance_control_set_id"]
    assert package["closing_docs"]["closing_docs_set_id"]
    assert package["payment_tracking"]["payment_tracking_set_id"]
    assert package["claim"]["claim_trigger_set_id"]
    assert package["deal_closure_report"]["deal_closure_report_set_id"]
    assert package["postmortem"]["postmortem_set_id"]
    assert package["supplier_rating"]["supplier_rating_update_set_id"]
    assert package["knowledge_asset"]["knowledge_asset_set_id"]
    assert package["workspace"]["workspace_feed_set_id"]
    assert package["action_queue"]["action_queue_set_id"]
    assert package["launch_visibility"]["launch_visibility_set_id"]

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    for code in {
        "quote_comparison_built",
        "supplier_contract_built",
        "execution_plan_built",
        "purchase_order_built",
        "logistics_tracking_built",
        "incident_register_built",
        "acceptance_control_built",
        "closing_docs_built",
        "payment_tracking_built",
        "claim_trigger_built",
        "deal_closure_report_set_created",
        "postmortem_set_created",
        "supplier_rating_set_created",
        "knowledge_asset_set_created",
        "workflow_run_built",
        "optimization_recommendations_built",
        "copilot_feed_built",
        "connector_registry_built",
        "connector_sync_finished",
        "workspace_feed_built",
        "action_queue_built",
        "action_queue_approved",
        "launch_visibility_built",
    }:
        assert code in event_codes


def test_dry_run_zero_visibility_and_manual_control_artifacts_persist(client, session):
    package = _execute_dry_run_zero(client, session)
    deal_id = package["intake"]["deal_id"]

    workspace_set = session.query(WorkspaceFeedSet).filter_by(
        workspace_feed_set_id=package["workspace"]["workspace_feed_set_id"]
    ).one()
    workspace_record = package["workspace"]["records"][0]
    workspace_items = session.query(WorkspaceFeedItem).filter_by(
        workspace_feed_id=workspace_record["workspace_feed_id"]
    ).all()

    queue_set = session.query(ActionQueueSet).filter_by(
        action_queue_set_id=package["action_queue"]["action_queue_set_id"]
    ).one()
    approvals = session.query(ActionQueueApproval).filter_by(
        action_queue_id=package["action_queue"]["records"][0]["action_queue_id"]
    ).all()

    visibility_set = session.query(LaunchVisibilitySet).filter_by(
        launch_visibility_set_id=package["launch_visibility"]["launch_visibility_set_id"]
    ).one()
    visibility_record = session.query(LaunchVisibilityRecord).filter_by(
        launch_visibility_set_id=package["launch_visibility"]["launch_visibility_set_id"]
    ).one()
    visibility_items = session.query(LaunchVisibilityItem).filter_by(
        launch_visibility_id=visibility_record.launch_visibility_id
    ).all()

    assert workspace_set.scope_ref == deal_id
    assert len(workspace_items) >= 1
    assert queue_set.scope_ref == deal_id
    assert len(approvals) == 1
    assert visibility_set.scope_ref == deal_id
    assert visibility_record.red_flag_count >= 2
    assert visibility_record.manual_review_count >= 1
    assert len(visibility_items) >= 4
