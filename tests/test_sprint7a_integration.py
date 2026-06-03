from src.modules.archive_export.models import ArchiveExportItem, ArchiveExportRecord, ArchiveExportSet
from src.modules.dashboard_snapshots.models import (
    DashboardMetricRecord,
    DashboardSnapshotRecord,
    DashboardSnapshotSet,
)
from src.modules.event_log.models import EventRecord
from src.modules.learning_automation.models import (
    LearningAutomationRecord,
    LearningAutomationSet,
    LearningRecommendationRecord,
)
from src.modules.kpi_learning.models import KPILearningSet
from tests.test_sprint6b_integration import _prepare_closed_deal_context, _prepare_completed_execution_context


def _prepare_operational_intelligence_context(client, session):
    package = _prepare_closed_deal_context(client, session)
    kpi = client.post(
        "/kpi-learning/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "learning_notes": [
                {"note_type": "PROCESS_GAP", "note_text": "Нужен финальный archive export checklist."},
                {"note_type": "SUPPLIER_LEARNING", "note_text": "Ранний прогрев поставщика ускоряет post-award launch."},
            ],
        },
    ).json()
    package["kpi"] = kpi
    return package


def test_build_dashboard_snapshot(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    response = client.post(
        "/dashboards/build",
        json={"scope_type": "DEAL", "scope_ref": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    snapshot_set = session.query(DashboardSnapshotSet).filter_by(
        dashboard_snapshot_set_id=payload["dashboard_snapshot_set_id"]
    ).one()
    assert snapshot_set.scope_ref == package["intake"]["deal_id"]
    assert snapshot_set.snapshot_status == "BUILT"


def test_dashboard_metric_records_persisted(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    payload = client.post(
        "/dashboards/build",
        json={"scope_type": "EXECUTION", "scope_ref": package["execution"]["execution_command_set_id"]},
    ).json()
    record = payload["records"][0]
    metrics = session.query(DashboardMetricRecord).filter_by(dashboard_snapshot_id=record["dashboard_snapshot_id"]).all()
    assert len(metrics) >= 4


def test_build_archive_export(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    response = client.post(
        "/archive-export/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "export_format": "JSON_BUNDLE",
        },
    )
    assert response.status_code == 201
    payload = response.json()

    export_set = session.query(ArchiveExportSet).filter_by(
        archive_export_set_id=payload["archive_export_set_id"]
    ).one()
    assert export_set.deal_id == package["intake"]["deal_id"]
    assert export_set.export_status == "BUILT"


def test_archive_export_items_persisted(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    payload = client.post(
        "/archive-export/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "mark_exported": True,
        },
    ).json()
    record = payload["records"][0]
    items = session.query(ArchiveExportItem).filter_by(archive_export_id=record["archive_export_id"]).all()
    assert len(items) >= 1
    assert payload["export_status"] == "EXPORTED"


def test_build_learning_automation(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    response = client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": package["intake"]["deal_id"],
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    automation_set = session.query(LearningAutomationSet).filter_by(
        learning_automation_set_id=payload["learning_automation_set_id"]
    ).one()
    assert automation_set.scope_ref == package["intake"]["deal_id"]


def test_learning_recommendations_persisted(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    payload = client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": package["intake"]["deal_id"],
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    ).json()
    record = payload["records"][0]
    recommendations = session.query(LearningRecommendationRecord).filter_by(
        learning_automation_id=record["learning_automation_id"]
    ).all()
    assert len(recommendations) >= 1


def test_sprint7a_outputs_linked_to_scope_and_deal(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    deal_id = package["intake"]["deal_id"]
    dashboard = client.post("/dashboards/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    export = client.post(
        "/archive-export/build",
        json={"deal_id": deal_id, "deal_closure_set_id": package["closure"]["deal_closure_set_id"]},
    ).json()
    learning = client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    ).json()

    assert session.query(DashboardSnapshotSet).filter_by(
        dashboard_snapshot_set_id=dashboard["dashboard_snapshot_set_id"], scope_ref=deal_id
    ).count() == 1
    assert session.query(ArchiveExportSet).filter_by(
        archive_export_set_id=export["archive_export_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(LearningAutomationSet).filter_by(
        learning_automation_set_id=learning["learning_automation_set_id"], scope_ref=deal_id
    ).count() == 1


def test_sprint7a_key_events_written(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    deal_id = package["intake"]["deal_id"]
    client.post("/dashboards/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    client.post(
        "/archive-export/build",
        json={"deal_id": deal_id, "deal_closure_set_id": package["closure"]["deal_closure_set_id"], "mark_exported": True},
    )
    client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    )

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "dashboard_snapshot_built" in event_codes
    assert "archive_export_built" in event_codes
    assert "archive_export_marked_exported" in event_codes
    assert "learning_automation_built" in event_codes
    assert "learning_recommendation_recorded" in event_codes


def test_closure_prerequisite_enforced_for_archive_export(client, session):
    package = _prepare_completed_execution_context(client, session)
    closure = client.post(
        "/deal-closure/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
        },
    ).json()
    response = client.post(
        "/archive-export/build",
        json={"deal_id": package["intake"]["deal_id"], "deal_closure_set_id": closure["deal_closure_set_id"]},
    )
    assert response.status_code == 422


def test_sprint7a_reruns_are_append_only(client, session):
    package = _prepare_operational_intelligence_context(client, session)
    deal_id = package["intake"]["deal_id"]
    first_dashboard = client.post("/dashboards/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    second_dashboard = client.post("/dashboards/build", json={"scope_type": "DEAL", "scope_ref": deal_id}).json()
    assert first_dashboard["dashboard_snapshot_set_id"] != second_dashboard["dashboard_snapshot_set_id"]

    first_learning = client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    ).json()
    second_learning = client.post(
        "/learning-automation/build",
        json={
            "scope_type": "DEAL",
            "scope_ref": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "kpi_learning_set_id": package["kpi"]["kpi_learning_set_id"],
        },
    ).json()
    assert first_learning["learning_automation_set_id"] != second_learning["learning_automation_set_id"]
    assert session.query(DashboardSnapshotSet).filter_by(scope_ref=deal_id).count() == 2
    assert session.query(LearningAutomationSet).filter_by(scope_ref=deal_id).count() == 2
