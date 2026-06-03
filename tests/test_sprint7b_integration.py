from src.modules.copilot_feed.models import CopilotFeedItem, CopilotFeedSet
from src.modules.event_log.models import EventRecord
from src.modules.optimization.models import (
    OptimizationRecommendationRecord,
    OptimizationRecommendationSet,
    OptimizationSignalRecord,
)
from src.modules.workflow_runs.models import WorkflowRunSet, WorkflowStepRecord
from tests.test_sprint6b_integration import _prepare_closed_deal_context
from tests.test_sprint7a_integration import _prepare_operational_intelligence_context


def _prepare_optimization_context(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    dashboard = client.post(
        "/dashboards/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    learning = client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": package["intake"]["deal_id"],
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    ).json()
    workflow = client.post(
        "/workflow-runs/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    package["dashboard"] = dashboard
    package["learning"] = learning
    package["workflow"] = workflow
    return package


def test_build_workflow_run(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    response = client.post(
        "/workflow-runs/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    workflow_set = session.query(WorkflowRunSet).filter_by(
        workflow_run_set_id=payload["workflow_run_set_id"]
    ).one()
    assert workflow_set.scope_ref == package["intake"]["deal_id"]


def test_workflow_steps_persisted(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    payload = client.post(
        "/workflow-runs/build",
        json={"scope_type": "EXECUTION", "scope_ref": package["execution"]["execution_command_set_id"]},
    ).json()
    record = payload["records"][0]
    steps = session.query(WorkflowStepRecord).filter_by(workflow_run_id=record["workflow_run_id"]).all()
    assert len(steps) >= 3


def test_build_optimization_recommendation_set(client, session):
    package = _prepare_optimization_context(client, session)
    response = client.post(
        "/optimization/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    optimization_set = session.query(OptimizationRecommendationSet).filter_by(
        optimization_recommendation_set_id=payload["optimization_recommendation_set_id"]
    ).one()
    assert optimization_set.scope_ref == package["intake"]["deal_id"]


def test_optimization_signals_persisted(client, session):
    package = _prepare_optimization_context(client, session)
    payload = client.post(
        "/optimization/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    summary_record = next(
        item for item in payload["records"] if item["recommendation_code"] == "OPTIMIZATION_SUMMARY"
    )
    signals = session.query(OptimizationSignalRecord).filter_by(
        optimization_recommendation_id=summary_record["optimization_recommendation_id"]
    ).all()
    assert len(signals) >= 3


def test_build_copilot_feed(client, session):
    package = _prepare_optimization_context(client, session)
    client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    response = client.post(
        "/copilot-feed/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    feed_set = session.query(CopilotFeedSet).filter_by(copilot_feed_set_id=payload["copilot_feed_set_id"]).one()
    assert feed_set.scope_ref == package["intake"]["deal_id"]


def test_copilot_feed_items_persisted(client, session):
    package = _prepare_optimization_context(client, session)
    client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]})
    payload = client.post(
        "/copilot-feed/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    ).json()
    record = payload["records"][0]
    items = session.query(CopilotFeedItem).filter_by(copilot_feed_id=record["copilot_feed_id"]).all()
    assert len(items) >= 1


def test_sprint7b_outputs_linked_to_scope_and_deal(client, session):
    package = _prepare_optimization_context(client, session)
    deal_id = package["intake"]["deal_id"]
    workflow = client.post("/workflow-runs/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    optimization = client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    feed = client.post("/copilot-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()

    assert session.query(WorkflowRunSet).filter_by(workflow_run_set_id=workflow["workflow_run_set_id"], scope_ref=deal_id).count() == 1
    assert session.query(OptimizationRecommendationSet).filter_by(
        optimization_recommendation_set_id=optimization["optimization_recommendation_set_id"], scope_ref=deal_id
    ).count() == 1
    assert session.query(CopilotFeedSet).filter_by(copilot_feed_set_id=feed["copilot_feed_set_id"], scope_ref=deal_id).count() == 1


def test_sprint7b_key_events_written(client, session):
    package = _prepare_optimization_context(client, session)
    deal_id = package["intake"]["deal_id"]
    client.post("/workflow-runs/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post("/copilot-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "workflow_run_built" in event_codes
    assert "workflow_step_recorded" in event_codes
    assert "optimization_recommendations_built" in event_codes
    assert "optimization_signal_recorded" in event_codes
    assert "copilot_feed_built" in event_codes
    assert "copilot_feed_item_recorded" in event_codes


def test_learning_prerequisite_enforced_for_deal_optimization(client, session):
    package = _prepare_closed_deal_context(client, session)
    response = client.post(
        "/optimization/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 422


def test_sprint7b_reruns_are_append_only(client, session):
    package = _prepare_optimization_context(client, session)
    deal_id = package["intake"]["deal_id"]

    first_workflow = client.post("/workflow-runs/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_workflow = client.post("/workflow-runs/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_workflow["workflow_run_set_id"] != second_workflow["workflow_run_set_id"]

    first_optimization = client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_optimization = client.post("/optimization/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_optimization["optimization_recommendation_set_id"] != second_optimization["optimization_recommendation_set_id"]

    client.post("/copilot-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post("/copilot-feed/build", json={"scope_type": "DEAL", "scope_ref": deal_id})

    assert session.query(WorkflowRunSet).filter_by(scope_ref=deal_id).count() >= 2
    assert session.query(OptimizationRecommendationSet).filter_by(scope_ref=deal_id).count() >= 2
    assert session.query(CopilotFeedSet).filter_by(scope_ref=deal_id).count() >= 2
