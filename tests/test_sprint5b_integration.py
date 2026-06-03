from src.modules.bid_completeness.models import BidCompletenessSet
from src.modules.bid_documents.models import BidDocumentCollectionSet
from src.modules.bid_packages.models import BidPackageItem, BidPackageSet
from src.modules.event_log.models import EventRecord
from src.modules.outcome_intake.models import OutcomeIntakeBinding, OutcomeIntakeRecord, OutcomeIntakeSet
from src.modules.post_submission.models import PostSubmissionEvent, PostSubmissionTrackerRecord, PostSubmissionTrackerSet
from src.modules.submission_control.models import SubmissionAttempt, SubmissionExecutionRecord, SubmissionExecutionSet
from src.modules.submission_readiness.models import SubmissionReadinessSet
from src.modules.submission_receipts.models import SubmissionReceiptBinding, SubmissionReceiptRecord, SubmissionReceiptSet
from tests.test_sprint5a_integration import _prepare_bid_prep_prerequisites


def _prepare_submission_prerequisites(client):
    package = _prepare_bid_prep_prerequisites(client)
    collection = client.post(
        "/bid-documents/collect",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
        },
    ).json()
    bid_package = client.post(
        "/bid-packages/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_document_collection_set_id": collection["bid_document_collection_set_id"],
        },
    ).json()
    completeness = client.post(
        "/bid-completeness/check",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_package_set_id": bid_package["bid_package_set_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
        },
    ).json()
    readiness = client.post(
        "/submission-readiness/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_completeness_set_id": completeness["bid_completeness_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "integrated_risk_memo_set_id": package["integrated_memo"]["integrated_risk_memo_set_id"],
        },
    ).json()
    package["collection"] = collection
    package["bid_package"] = bid_package
    package["completeness"] = completeness
    package["readiness"] = readiness
    return package


def _prepare_submitted_execution(client):
    package = _prepare_submission_prerequisites(client)
    control = client.post(
        "/submission-control/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_readiness_set_id": package["readiness"]["submission_readiness_set_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    ).json()
    execution = client.post(
        "/submission-control/start",
        json={
            "submission_execution_set_id": control["submission_execution_set_id"],
            "channel_type": "MANUAL",
            "initiated_by_ref": "OPS-1",
        },
    ).json()
    client.post(
        "/submission-control/attempts",
        json={
            "submission_execution_id": execution["submission_execution_id"],
            "attempt_no": 1,
            "attempt_status": "STARTED",
            "notes": "Начали ручную подачу.",
        },
    )
    client.post(
        "/submission-control/attempts",
        json={
            "submission_execution_id": execution["submission_execution_id"],
            "attempt_no": 2,
            "attempt_status": "SUCCEEDED",
            "notes": "Подача прошла успешно.",
        },
    )
    package["submission_control"] = control
    package["submission_execution"] = execution
    return package


def test_build_submission_control_and_persist_set(client, session):
    package = _prepare_submission_prerequisites(client)
    response = client.post(
        "/submission-control/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_readiness_set_id": package["readiness"]["submission_readiness_set_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    execution_set = session.query(SubmissionExecutionSet).filter_by(
        submission_execution_set_id=payload["submission_execution_set_id"]
    ).one()
    assert execution_set.deal_id == package["intake"]["deal_id"]
    assert execution_set.execution_status == "READY"
    assert payload["records"] == []


def test_start_submission_execution_and_attempts_append_only(client, session):
    package = _prepare_submission_prerequisites(client)
    control = client.post(
        "/submission-control/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_readiness_set_id": package["readiness"]["submission_readiness_set_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    ).json()
    start = client.post(
        "/submission-control/start",
        json={
            "submission_execution_set_id": control["submission_execution_set_id"],
            "channel_type": "PORTAL",
            "initiated_by_ref": "OPS-2",
        },
    )
    assert start.status_code == 201
    execution = start.json()
    attempt_1 = client.post(
        "/submission-control/attempts",
        json={
            "submission_execution_id": execution["submission_execution_id"],
            "attempt_no": 1,
            "attempt_status": "STARTED",
            "notes": "Открыли сессию подачи.",
        },
    )
    attempt_2 = client.post(
        "/submission-control/attempts",
        json={
            "submission_execution_id": execution["submission_execution_id"],
            "attempt_no": 2,
            "attempt_status": "FAILED",
            "notes": "ЭТП вернула техническую ошибку.",
        },
    )
    assert attempt_1.status_code == 201
    assert attempt_2.status_code == 201

    record = session.query(SubmissionExecutionRecord).filter_by(
        submission_execution_id=execution["submission_execution_id"]
    ).one()
    attempts = session.query(SubmissionAttempt).filter_by(submission_execution_id=execution["submission_execution_id"]).all()
    execution_set = session.query(SubmissionExecutionSet).filter_by(
        submission_execution_set_id=control["submission_execution_set_id"]
    ).one()

    assert record.channel_type == "PORTAL"
    assert len(attempts) == 2
    assert execution_set.execution_status == "FAILED"


def test_submission_receipt_requires_submitted_execution(client):
    package = _prepare_submission_prerequisites(client)
    control = client.post(
        "/submission-control/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_readiness_set_id": package["readiness"]["submission_readiness_set_id"],
            "bid_package_set_id": package["bid_package"]["bid_package_set_id"],
        },
    ).json()
    response = client.post(
        "/submission-receipts/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": control["submission_execution_set_id"],
            "receipt_number": "ETP-00001",
            "receipt_timestamp": "2026-06-03T10:00:00Z",
            "receipt_source": "PORTAL",
            "bindings": [],
        },
    )
    assert response.status_code == 422


def test_register_submission_receipt_and_persist_bindings(client, session):
    package = _prepare_submitted_execution(client)
    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    response = client.post(
        "/submission-receipts/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
            "receipt_number": "ETP-123456",
            "receipt_timestamp": "2026-06-03T10:00:00Z",
            "receipt_source": "PORTAL",
            "bindings": [
                {"artifact_ref": artifact_ref, "binding_type": "SCREENSHOT"},
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    receipt_set = session.query(SubmissionReceiptSet).filter_by(
        submission_receipt_set_id=payload["submission_receipt_set_id"]
    ).one()
    receipt_record = session.query(SubmissionReceiptRecord).filter_by(
        submission_receipt_set_id=payload["submission_receipt_set_id"]
    ).one()
    bindings = session.query(SubmissionReceiptBinding).filter_by(
        submission_receipt_id=receipt_record.submission_receipt_id
    ).all()

    assert receipt_set.deal_id == package["intake"]["deal_id"]
    assert receipt_set.receipt_status == "REGISTERED"
    assert len(bindings) == 1


def test_build_post_submission_tracker_and_persist_events(client, session):
    package = _prepare_submitted_execution(client)
    response = client.post(
        "/post-submission/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
        },
    )
    assert response.status_code == 201
    tracker = response.json()
    tracker_record = tracker["records"][0]

    event_1 = client.post(
        "/post-submission/events",
        json={
            "post_submission_tracker_id": tracker_record["post_submission_tracker_id"],
            "event_type": "STATUS_UPDATE",
            "summary": "Заявка принята к рассмотрению.",
            "stage": "UNDER_REVIEW",
        },
    )
    event_2 = client.post(
        "/post-submission/events",
        json={
            "post_submission_tracker_id": tracker_record["post_submission_tracker_id"],
            "event_type": "NOTICE",
            "summary": "Опубликован итоговый протокол.",
            "stage": "AWARDED",
            "source_ref": "PROTO-1",
        },
    )
    assert event_1.status_code == 201
    assert event_2.status_code == 201

    tracker_set = session.query(PostSubmissionTrackerSet).filter_by(
        post_submission_tracker_set_id=tracker["post_submission_tracker_set_id"]
    ).one()
    record = session.query(PostSubmissionTrackerRecord).filter_by(
        post_submission_tracker_set_id=tracker["post_submission_tracker_set_id"]
    ).one()
    events = session.query(PostSubmissionEvent).filter_by(
        post_submission_tracker_id=record.post_submission_tracker_id
    ).all()

    assert tracker_set.tracker_status == "CLOSED"
    assert record.current_stage == "AWARDED"
    assert len(events) == 2


def test_register_outcome_intake_and_persist_bindings(client, session):
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
            "summary": "Опубликован итоговый протокол победителя.",
            "stage": "AWARDED",
        },
    )
    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    response = client.post(
        "/outcome-intake/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "post_submission_tracker_set_id": tracker["post_submission_tracker_set_id"],
            "outcome_code": "WON",
            "effective_at": "2026-06-10T12:00:00Z",
            "rationale": "Победа по итогам рассмотрения.",
            "bindings": [
                {"artifact_ref": artifact_ref, "binding_type": "NOTICE"},
            ],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    outcome_set = session.query(OutcomeIntakeSet).filter_by(
        outcome_intake_set_id=payload["outcome_intake_set_id"]
    ).one()
    outcome_record = session.query(OutcomeIntakeRecord).filter_by(
        outcome_intake_set_id=payload["outcome_intake_set_id"]
    ).one()
    bindings = session.query(OutcomeIntakeBinding).filter_by(
        outcome_intake_id=outcome_record.outcome_intake_id
    ).all()

    assert outcome_set.deal_id == package["intake"]["deal_id"]
    assert outcome_set.outcome_status == "RECORDED"
    assert len(bindings) == 1


def test_sprint5b_outputs_linked_to_deal_and_events_written(client, session):
    package = _prepare_submitted_execution(client)
    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    receipt = client.post(
        "/submission-receipts/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
            "receipt_number": "ETP-999999",
            "receipt_timestamp": "2026-06-03T10:30:00Z",
            "receipt_source": "PORTAL",
            "bindings": [
                {"artifact_ref": artifact_ref, "binding_type": "PDF"},
            ],
        },
    ).json()
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
            "summary": "Опубликован итоговый протокол об отклонении.",
            "stage": "LOST",
        },
    )
    outcome = client.post(
        "/outcome-intake/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "post_submission_tracker_set_id": tracker["post_submission_tracker_set_id"],
            "outcome_code": "LOST",
            "effective_at": "2026-06-11T09:00:00Z",
            "rationale": "Проиграли по цене.",
            "bindings": [
                {"artifact_ref": artifact_ref, "binding_type": "PROTOCOL"},
            ],
        },
    ).json()

    deal_id = package["intake"]["deal_id"]
    assert session.query(BidDocumentCollectionSet).filter_by(
        bid_document_collection_set_id=package["collection"]["bid_document_collection_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(BidPackageSet).filter_by(
        bid_package_set_id=package["bid_package"]["bid_package_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(BidCompletenessSet).filter_by(
        bid_completeness_set_id=package["completeness"]["bid_completeness_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(SubmissionReadinessSet).filter_by(
        submission_readiness_set_id=package["readiness"]["submission_readiness_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(SubmissionExecutionSet).filter_by(
        submission_execution_set_id=package["submission_control"]["submission_execution_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(SubmissionReceiptSet).filter_by(
        submission_receipt_set_id=receipt["submission_receipt_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(PostSubmissionTrackerSet).filter_by(
        post_submission_tracker_set_id=tracker["post_submission_tracker_set_id"], deal_id=deal_id
    ).count() == 1
    assert session.query(OutcomeIntakeSet).filter_by(
        outcome_intake_set_id=outcome["outcome_intake_set_id"], deal_id=deal_id
    ).count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "submission_control_built" in event_codes
    assert "submission_execution_started" in event_codes
    assert "submission_attempt_recorded" in event_codes
    assert "submission_execution_submitted" in event_codes
    assert "submission_receipt_registered" in event_codes
    assert "post_submission_tracker_built" in event_codes
    assert "post_submission_event_recorded" in event_codes
    assert "post_submission_tracker_closed" in event_codes
    assert "outcome_intake_recorded" in event_codes


def test_sprint5b_append_only_reruns(client, session):
    package = _prepare_submitted_execution(client)
    first_tracker = client.post(
        "/post-submission/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
        },
    ).json()
    second_tracker = client.post(
        "/post-submission/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "submission_execution_set_id": package["submission_control"]["submission_execution_set_id"],
        },
    ).json()
    assert first_tracker["post_submission_tracker_set_id"] != second_tracker["post_submission_tracker_set_id"]

    artifact_ref = session.query(BidPackageItem).first().artifact_ref
    first_outcome = client.post(
        "/outcome-intake/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "post_submission_tracker_set_id": first_tracker["post_submission_tracker_set_id"],
            "outcome_code": "NO_RESULT",
            "effective_at": "2026-06-12T10:00:00Z",
            "rationale": "Итог еще не опубликован.",
            "bindings": [
                {"artifact_ref": artifact_ref, "binding_type": "EMAIL"},
            ],
        },
    ).json()
    second_outcome = client.post(
        "/outcome-intake/register",
        json={
            "deal_id": package["intake"]["deal_id"],
            "post_submission_tracker_set_id": first_tracker["post_submission_tracker_set_id"],
            "outcome_code": "WON",
            "effective_at": "2026-06-13T10:00:00Z",
            "rationale": "Позже пришло официальное подтверждение победы.",
            "bindings": [
                {"artifact_ref": artifact_ref, "binding_type": "NOTICE"},
            ],
        },
    ).json()

    assert first_outcome["outcome_intake_set_id"] != second_outcome["outcome_intake_set_id"]
    second_set = session.query(OutcomeIntakeSet).filter_by(
        outcome_intake_set_id=second_outcome["outcome_intake_set_id"]
    ).one()
    assert second_set.outcome_status == "REVISED"
    assert session.query(PostSubmissionTrackerSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == 2
    assert session.query(OutcomeIntakeSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == 2
