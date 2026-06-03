from src.modules.bid_completeness.models import BidCompletenessFlag, BidCompletenessRecord, BidCompletenessSet
from src.modules.bid_documents.models import (
    BidDocumentCollectionBinding,
    BidDocumentCollectionRow,
    BidDocumentCollectionSet,
)
from src.modules.bid_packages.models import BidPackageItem, BidPackageRecord, BidPackageSet
from src.modules.document_requirements.models import DocumentRequirementRow, DocumentRequirementSet
from src.modules.event_log.models import EventRecord
from src.modules.submission_readiness.models import (
    SubmissionReadinessFlag,
    SubmissionReadinessRecord,
    SubmissionReadinessSet,
)
from tests.test_sprint4b_integration import _prepare_risk_approval_prerequisites


def _prepare_bid_prep_prerequisites(client):
    package = _prepare_risk_approval_prerequisites(client)
    contract_risks = client.post(
        "/contract-risks/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_set_id": package["document_set"]["document_set_id"],
        },
    ).json()
    integrated_memo = client.post(
        "/integrated-risk-memo/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "initial_tech_risk_flag_set_id": package["risks"]["risk_flag_set_id"],
            "supplier_verification_set_id": package["verification"]["supplier_verification_set_id"],
            "quote_comparison_set_id": package["comparison"]["quote_comparison_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "contract_risk_set_id": contract_risks["contract_risk_set_id"],
        },
    ).json()
    approval_set = client.post(
        "/ceo-approval/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "integrated_risk_memo_set_id": integrated_memo["integrated_risk_memo_set_id"],
        },
    ).json()
    client.post(
        "/ceo-approval/decide",
        json={
            "ceo_approval_set_id": approval_set["ceo_approval_set_id"],
            "decision": "GO",
            "decided_by_ref": "CEO",
            "rationale": "Пакет можно готовить к подаче.",
            "conditions": [],
        },
    )
    package["contract_risks"] = contract_risks
    package["integrated_memo"] = integrated_memo
    package["approval_set"] = approval_set
    return package


def test_build_bid_document_collection_and_persist_rows_bindings(client, session):
    package = _prepare_bid_prep_prerequisites(client)
    response = client.post(
        "/bid-documents/collect",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    collection_set = session.query(BidDocumentCollectionSet).filter_by(
        bid_document_collection_set_id=payload["bid_document_collection_set_id"]
    ).one()
    rows = session.query(BidDocumentCollectionRow).filter_by(
        bid_document_collection_set_id=payload["bid_document_collection_set_id"]
    ).all()
    bindings = session.query(BidDocumentCollectionBinding).filter_by(
        bid_document_collection_set_id=payload["bid_document_collection_set_id"]
    ).all()

    assert collection_set.deal_id == package["intake"]["deal_id"]
    assert len(rows) >= 1
    assert len(bindings) >= 1
    assert any(row.collection_status == "COLLECTED" for row in rows)


def test_collection_can_persist_missing_states(client, session):
    package = _prepare_bid_prep_prerequisites(client)
    requirement_set = session.query(DocumentRequirementSet).filter_by(
        document_requirement_set_id=package["requirements"]["document_requirement_set_id"]
    ).one()
    session.add(
        DocumentRequirementRow(
            document_requirement_set_id=requirement_set.document_requirement_set_id,
            row_code="DR-9999",
            sequence_no=9999,
            requirement_title="Декларация об отсутствии конфликта интересов",
            requirement_description="Требуется отдельная bid-prep декларация",
            requirement_category="DECLARATION",
            requirement_status="REQUIRED",
            source_artifact_ref=None,
            source_pointer="SYNTHETIC:DECLARATION",
            notes="Synthetic test requirement",
            requires_manual_review=False,
        )
    )
    requirement_set.requirement_count += 1
    session.add(requirement_set)
    session.commit()

    response = client.post(
        "/bid-documents/collect",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()
    rows = session.query(BidDocumentCollectionRow).filter_by(
        bid_document_collection_set_id=payload["bid_document_collection_set_id"]
    ).all()

    assert any(row.collection_status == "MISSING" for row in rows)


def test_build_bid_package_and_persist_manifest_items(client, session):
    package = _prepare_bid_prep_prerequisites(client)
    collection = client.post(
        "/bid-documents/collect",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
        },
    ).json()

    response = client.post(
        "/bid-packages/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_document_collection_set_id": collection["bid_document_collection_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    package_set = session.query(BidPackageSet).filter_by(bid_package_set_id=payload["bid_package_set_id"]).one()
    record = session.query(BidPackageRecord).filter_by(bid_package_set_id=payload["bid_package_set_id"]).one()
    items = session.query(BidPackageItem).filter_by(bid_package_id=record.bid_package_id).all()

    assert package_set.deal_id == package["intake"]["deal_id"]
    assert record.manifest_json["item_count"] == len(items)
    assert len(items) >= 1


def test_check_bid_completeness_and_persist_flags(client, session):
    package = _prepare_bid_prep_prerequisites(client)
    requirement_set = session.query(DocumentRequirementSet).filter_by(
        document_requirement_set_id=package["requirements"]["document_requirement_set_id"]
    ).one()
    session.add(
        DocumentRequirementRow(
            document_requirement_set_id=requirement_set.document_requirement_set_id,
            row_code="DR-8888",
            sequence_no=8888,
            requirement_title="Обязательная декларация",
            requirement_description="Требуется для полноты заявки",
            requirement_category="DECLARATION",
            requirement_status="REQUIRED",
            source_artifact_ref=None,
            source_pointer="SYNTHETIC:DECLARATION",
            notes=None,
            requires_manual_review=False,
        )
    )
    requirement_set.requirement_count += 1
    session.add(requirement_set)
    session.commit()

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

    response = client.post(
        "/bid-completeness/check",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_package_set_id": bid_package["bid_package_set_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
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

    assert completeness_set.deal_id == package["intake"]["deal_id"]
    assert completeness_set.completeness_status in {"COMPLETE", "INCOMPLETE", "NEEDS_REVIEW"}
    assert len(flags) >= 1


def test_build_submission_readiness_and_persist_recommendation(client, session):
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

    response = client.post(
        "/submission-readiness/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_completeness_set_id": completeness["bid_completeness_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
            "finance_memo_set_id": package["finance_memo"]["finance_memo_set_id"],
            "integrated_risk_memo_set_id": package["integrated_memo"]["integrated_risk_memo_set_id"],
        },
    )
    assert response.status_code == 201
    payload = response.json()

    readiness_set = session.query(SubmissionReadinessSet).filter_by(
        submission_readiness_set_id=payload["submission_readiness_set_id"]
    ).one()
    record = session.query(SubmissionReadinessRecord).filter_by(
        submission_readiness_set_id=payload["submission_readiness_set_id"]
    ).one()
    flags = session.query(SubmissionReadinessFlag).filter_by(
        submission_readiness_id=record.submission_readiness_id
    ).all()

    assert readiness_set.deal_id == package["intake"]["deal_id"]
    assert record.recommendation in {"READY", "NOT_READY", "NEEDS_REVIEW"}
    assert len(flags) >= 0


def test_sprint5a_outputs_linked_to_deal_and_events_written(client, session):
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

    assert session.query(BidDocumentCollectionSet).filter_by(
        bid_document_collection_set_id=collection["bid_document_collection_set_id"], deal_id=package["intake"]["deal_id"]
    ).count() == 1
    assert session.query(BidPackageSet).filter_by(
        bid_package_set_id=bid_package["bid_package_set_id"], deal_id=package["intake"]["deal_id"]
    ).count() == 1
    assert session.query(BidCompletenessSet).filter_by(
        bid_completeness_set_id=completeness["bid_completeness_set_id"], deal_id=package["intake"]["deal_id"]
    ).count() == 1
    assert session.query(SubmissionReadinessSet).filter_by(
        submission_readiness_set_id=readiness["submission_readiness_set_id"], deal_id=package["intake"]["deal_id"]
    ).count() == 1

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=package["intake"]["deal_id"]).all()}
    assert "bid_document_collection_started" in event_codes
    assert "bid_document_collection_built" in event_codes
    assert "bid_package_build_started" in event_codes
    assert "bid_package_built" in event_codes
    assert "bid_completeness_check_started" in event_codes
    assert "bid_completeness_checked" in event_codes
    assert "submission_readiness_build_started" in event_codes
    assert "submission_readiness_built" in event_codes


def test_sprint5a_reruns_are_append_only(client, session):
    package = _prepare_bid_prep_prerequisites(client)
    first_collection = client.post(
        "/bid-documents/collect",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
        },
    ).json()
    second_collection = client.post(
        "/bid-documents/collect",
        json={
            "deal_id": package["intake"]["deal_id"],
            "document_requirement_set_id": package["requirements"]["document_requirement_set_id"],
            "ceo_approval_set_id": package["approval_set"]["ceo_approval_set_id"],
        },
    ).json()
    assert first_collection["bid_document_collection_set_id"] != second_collection["bid_document_collection_set_id"]

    first_package = client.post(
        "/bid-packages/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_document_collection_set_id": first_collection["bid_document_collection_set_id"],
        },
    ).json()
    second_package = client.post(
        "/bid-packages/build",
        json={
            "deal_id": package["intake"]["deal_id"],
            "bid_document_collection_set_id": second_collection["bid_document_collection_set_id"],
        },
    ).json()
    assert first_package["bid_package_set_id"] != second_package["bid_package_set_id"]
    assert session.query(BidDocumentCollectionSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == 2
    assert session.query(BidPackageSet).filter_by(deal_id=package["intake"]["deal_id"]).count() == 2
