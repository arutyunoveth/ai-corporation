from src.modules.bid_completeness.models import (
    BidCompletenessFlag,
    BidCompletenessRecord,
    BidCompletenessSet,
    BidReadinessReport,
)
from src.modules.contract_negotiation.models import (
    ContractNegotiationComment,
    ContractNegotiationIssue,
    ContractNegotiationRecord,
    ContractNegotiationSet,
)
from src.modules.event_log.models import EventRecord
from src.modules.outcome_intake.models import OutcomeIntakeSet
from src.modules.procedure_monitor.models import (
    ProcedureMonitorAlert,
    ProcedureMonitorEvent,
    ProcedureMonitorRecord,
    ProcedureMonitorSet,
)
from src.modules.submission_archive.models import (
    SubmissionArchiveItem,
    SubmissionArchiveRecord,
    SubmissionArchiveSet,
)
from tests.test_sprint5b_integration import _prepare_submission_prerequisites, _prepare_submitted_execution


def _register_receipt_for_execution(client, package, artifact_ref: str):
    response = client.post(
        "/submission-receipts/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
            "receipt_number": "ETP-R2-0001",
            "receipt_timestamp": "2026-06-04T08:00:00Z",
            "receipt_source": "PORTAL",
            "bindings": [{"artifact_ref": artifact_ref, "binding_type": "SCREENSHOT"}],
        },
    )
    assert response.status_code == 201
    return response.json()


def _prepare_won_monitor_context(client, session):
    package = _prepare_submitted_execution(client)
    # Use any bid package artifact as evidence for receipt/outcome helpers.
    from src.modules.bid_packages.models import BidPackageItem

    bid_artifact_ref = session.query(BidPackageItem).first().artifact_ref
    _register_receipt_for_execution(client, package, bid_artifact_ref)
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
            "event_type": "STATUS_UPDATE",
            "summary": "Заявка принята к рассмотрению.",
            "stage": "UNDER_REVIEW",
        },
    )
    client.post(
        "/post-submission/events",
        json={
            "post_submission_tracker_id": tracker_record["post_submission_tracker_id"],
            "event_type": "NOTICE",
            "summary": "Победа подтверждена итоговым протоколом.",
            "stage": "AWARDED",
            "source_ref": "PROTO-WIN-1",
        },
    )
    outcome = client.post(
        "/outcome-intake/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "post_submission_tracker_set_id": tracker["post_submission_tracker_set_id"],
            "outcome_code": "WON",
            "effective_at": "2026-06-12T10:00:00Z",
            "rationale": "Победа подтверждена по итоговому протоколу.",
            "bindings": [{"artifact_ref": bid_artifact_ref, "binding_type": "PROTOCOL"}],
        },
    )
    assert outcome.status_code == 201
    package["tracker"] = tracker
    package["outcome"] = outcome.json()
    package["artifact_ref"] = bid_artifact_ref
    return package


def test_bid_completeness_persists_readiness_report(client, session):
    package = _prepare_submission_prerequisites(client)
    prior_event_count = session.query(EventRecord).filter_by(event_code="bid_readiness_report_built").count()
    response = client.post(
        "/bid-completeness/check",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    completeness_set = session.query(BidCompletenessSet).filter_by(
        bid_completeness_set_id=payload["bid_completeness_set_id"]
    ).one()
    record = session.query(BidCompletenessRecord).filter_by(
        bid_completeness_set_id=payload["bid_completeness_set_id"]
    ).one()
    flags = session.query(BidCompletenessFlag).filter_by(bid_completeness_id=record.bid_completeness_id).all()
    reports = session.query(BidReadinessReport).filter_by(
        bid_completeness_set_id=payload["bid_completeness_set_id"]
    ).all()

    assert completeness_set.deal_id == package["intake"]["deal_id"]
    assert len(reports) == 1
    assert reports[0].blocking_issue_count >= 0
    assert "readiness_reports" in payload
    assert session.query(EventRecord).filter_by(event_code="bid_readiness_report_built").count() == prior_event_count + 1
    assert len(flags) >= 0


def test_submission_archive_build_and_item_persistence(client, session):
    package = _prepare_submitted_execution(client)
    from src.modules.bid_packages.models import BidPackageItem

    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    _register_receipt_for_execution(client, package, artifact_ref)

    response = client.post(
        "/submission-archive/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    archive_set = session.query(SubmissionArchiveSet).filter_by(
        submission_archive_set_id=payload["submission_archive_set_id"]
    ).one()
    archive_record = session.query(SubmissionArchiveRecord).filter_by(
        submission_archive_set_id=payload["submission_archive_set_id"]
    ).one()
    items = session.query(SubmissionArchiveItem).filter_by(
        submission_archive_id=archive_record.submission_archive_id
    ).all()

    assert archive_set.deal_id == package["intake"]["deal_id"]
    assert archive_set.archive_status == "BUILT"
    assert archive_record.archive_manifest_json["receipt_binding_count"] >= 1
    assert len(items) >= 2
    assert session.query(EventRecord).filter_by(event_code="submission_archive_built").count() == 1


def test_procedure_monitor_build_and_event_alert_persistence(client, session):
    package = _prepare_won_monitor_context(client, session)
    response = client.post(
        "/procedure-monitor/build",
        json={"deal_id": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    monitor_set = session.query(ProcedureMonitorSet).filter_by(
        procedure_monitor_set_id=payload["procedure_monitor_set_id"]
    ).one()
    monitor_record = session.query(ProcedureMonitorRecord).filter_by(
        procedure_monitor_set_id=payload["procedure_monitor_set_id"]
    ).one()
    initial_events = session.query(ProcedureMonitorEvent).filter_by(
        procedure_monitor_id=monitor_record.procedure_monitor_id
    ).all()
    initial_alerts = session.query(ProcedureMonitorAlert).filter_by(
        procedure_monitor_id=monitor_record.procedure_monitor_id
    ).all()

    assert monitor_set.procedure_status == "WON_PENDING_CONTRACT"
    assert len(initial_events) >= 2
    assert len(initial_alerts) >= 1

    event_response = client.post(
        "/procedure-monitor/events",
        json={
            "procedure_monitor_id": monitor_record.procedure_monitor_id,
            "event_type": "ALERT",
            "summary": "Требуется срочно согласовать условия контракта.",
            "current_stage": "AWARDED",
        },
    )
    assert event_response.status_code == 201
    alerts = session.query(ProcedureMonitorAlert).filter_by(
        procedure_monitor_id=monitor_record.procedure_monitor_id
    ).all()
    assert any(alert.alert_code == "MANUAL_ALERT" for alert in alerts)
    assert session.query(EventRecord).filter_by(event_code="procedure_monitor_built").count() == 1
    assert session.query(EventRecord).filter_by(event_code="procedure_monitor_event_recorded").count() == 1


def test_contract_negotiation_workspace_build_and_issue_comment_persistence(client, session):
    package = _prepare_won_monitor_context(client, session)
    client.post("/procedure-monitor/build", json={"deal_id": package["intake"]["deal_id"]})

    response = client.post(
        "/contract-negotiation/build",
        json={"deal_id": package["intake"]["deal_id"]},
    )
    assert response.status_code == 201
    payload = response.json()

    negotiation_set = session.query(ContractNegotiationSet).filter_by(
        contract_negotiation_set_id=payload["contract_negotiation_set_id"]
    ).one()
    record = session.query(ContractNegotiationRecord).filter_by(
        contract_negotiation_set_id=payload["contract_negotiation_set_id"]
    ).one()
    issues = session.query(ContractNegotiationIssue).filter_by(
        contract_negotiation_id=record.contract_negotiation_id
    ).all()
    comments = session.query(ContractNegotiationComment).filter_by(
        contract_negotiation_id=record.contract_negotiation_id
    ).all()

    assert negotiation_set.deal_id == package["intake"]["deal_id"]
    assert record.negotiation_pack_manifest_json["outcome_binding_count"] >= 1
    assert len(comments) >= 1
    assert len(issues) >= 0
    assert session.query(OutcomeIntakeSet).filter_by(deal_id=package["intake"]["deal_id"]).count() >= 1
    assert session.query(EventRecord).filter_by(event_code="contract_negotiation_built").count() == 1


def test_recovery_r2_outputs_query_by_deal_and_reruns_append_only(client, session):
    package = _prepare_won_monitor_context(client, session)
    from src.modules.bid_packages.models import BidPackageItem

    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    _register_receipt_for_execution(client, package, artifact_ref)
    client.post(
        "/submission-archive/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    )
    client.post(
        "/submission-archive/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    )
    client.post("/procedure-monitor/build", json={"deal_id": package["intake"]["deal_id"]})
    client.post("/procedure-monitor/build", json={"deal_id": package["intake"]["deal_id"]})

    archives = client.get("/submission-archive", params={"deal_id": package["intake"]["deal_id"]})
    monitors = client.get("/procedure-monitor", params={"deal_id": package["intake"]["deal_id"]})
    negotiations = client.get("/contract-negotiation", params={"deal_id": package["intake"]["deal_id"]})

    client.post("/contract-negotiation/build", json={"deal_id": package["intake"]["deal_id"]})

    assert archives.status_code == 200
    assert monitors.status_code == 200
    assert negotiations.status_code == 200
    assert session.query(SubmissionArchiveSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == 2
    assert session.query(ProcedureMonitorSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == 2
    assert session.query(ContractNegotiationSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == 1
