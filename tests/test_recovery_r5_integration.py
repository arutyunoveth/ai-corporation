from src.modules.deal_closure_reports.models import (
    DealClosureReportLink,
    DealClosureReportRecord,
    DealClosureReportSet,
)
from src.modules.event_log.models import EventRecord
from src.modules.knowledge_assets.models import KnowledgeAssetLink, KnowledgeAssetRecord, KnowledgeAssetSet
from src.modules.postmortems.models import (
    PostmortemActionItem,
    PostmortemFinding,
    PostmortemRecord,
    PostmortemSet,
)
from src.modules.supplier_ratings.models import (
    SupplierRatingFactor,
    SupplierRatingUpdateRecord,
    SupplierRatingUpdateSet,
)
from tests.test_recovery_r4_integration import _prepare_r4_payment_context


def _prepare_r5_final_context(client, session):
    package = _prepare_r4_payment_context(client, session)
    deal_id = package["intake"]["deal_id"]

    payment_helper_record = package["payment_helper"]["records"][0]
    assert (
        client.post(
            "/payment-collection/events",
            json={
                "payment_collection_id": payment_helper_record["payment_collection_id"],
                "summary": "Счет выставлен заказчику.",
                "collection_state": "INVOICED",
                "invoice_ref": "INV-R5-001",
            },
        ).status_code
        == 201
    )
    assert (
        client.post(
            "/payment-collection/events",
            json={
                "payment_collection_id": payment_helper_record["payment_collection_id"],
                "summary": "Оплата получена в полном объеме.",
                "collection_state": "COLLECTED",
                "collected_amount": payment_helper_record["expected_amount"],
            },
        ).status_code
        == 201
    )

    incident_register = client.post("/incident-register/build", json={"deal_id": deal_id})
    assert incident_register.status_code == 201
    package["incident_register"] = incident_register.json()
    incident_record = package["incident_register"]["records"][0]
    assert (
        client.post(
            "/incident-register/events",
            json={
                "incident_register_id": incident_record["incident_register_id"],
                "event_type": "NOTE",
                "summary": "Инцидент сохранен для closure/postmortem анализа.",
                "severity": "MEDIUM",
            },
        ).status_code
        == 201
    )

    payment_tracking = client.post("/payment-tracking/build", json={"deal_id": deal_id})
    assert payment_tracking.status_code == 201
    package["payment_tracking"] = payment_tracking.json()
    payment_tracking_record = package["payment_tracking"]["records"][0]
    assert (
        client.post(
            "/payment-tracking/events",
            json={
                "payment_tracking_id": payment_tracking_record["payment_tracking_id"],
                "event_type": "OVERDUE",
                "summary": "Заказчик задержал финальный транш, нужен claim trace.",
                "overdue_days": 5,
                "payment_status": "OVERDUE",
            },
        ).status_code
        == 201
    )

    claim = client.post("/claim-triggers/build", json={"deal_id": deal_id})
    assert claim.status_code == 201
    package["claim"] = claim.json()

    closure = client.post(
        "/deal-closure/build",
        json={
            "deal_id": deal_id,
            "outcome_intake_set_id": package["outcome"]["outcome_intake_set_id"],
            "execution_command_set_id": package["execution"]["execution_command_set_id"],
        },
    )
    assert closure.status_code == 201
    closed = client.post(
        "/deal-closure/close",
        json={
            "deal_closure_set_id": closure.json()["deal_closure_set_id"],
            "summary_text": "Сделка закрыта после исполнения, но с late payment signal.",
        },
    )
    assert closed.status_code == 200
    package["closure"] = closed.json()

    kpi = client.post(
        "/kpi-learning/build",
        json={
            "deal_id": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "learning_notes": [
                {"note_type": "PROCESS_GAP", "note_text": "Payment follow-up should start earlier."},
                {"note_type": "SUPPLIER_LEARNING", "note_text": "Supplier fulfilled execution despite payment friction."},
            ],
        },
    )
    assert kpi.status_code == 201
    package["kpi"] = kpi.json()

    dashboard = client.post("/dashboards/build", json={"scope_type": "DEAL", "scope_ref": deal_id})
    assert dashboard.status_code == 201
    package["dashboard"] = dashboard.json()

    archive = client.post(
        "/archive-export/build",
        json={
            "deal_id": deal_id,
            "deal_closure_set_id": package["closure"]["deal_closure_set_id"],
            "mark_exported": True,
        },
    )
    assert archive.status_code == 201
    package["archive"] = archive.json()
    return package


def test_build_deal_closure_report_and_persist_links(client, session):
    package = _prepare_r5_final_context(client, session)
    response = client.post("/deal-closure-reports/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    report_set = session.query(DealClosureReportSet).filter_by(
        deal_closure_report_set_id=payload["deal_closure_report_set_id"]
    ).one()
    report_record = session.query(DealClosureReportRecord).filter_by(
        deal_closure_report_set_id=payload["deal_closure_report_set_id"]
    ).one()
    links = session.query(DealClosureReportLink).filter_by(
        deal_closure_report_id=report_record.deal_closure_report_id
    ).all()

    assert report_set.deal_id == package["intake"]["deal_id"]
    assert report_set.claim_trigger_set_id == package["claim"]["claim_trigger_set_id"]
    assert len(links) >= 4


def test_build_postmortem_and_persist_findings_actions(client, session):
    package = _prepare_r5_final_context(client, session)
    report = client.post("/deal-closure-reports/build", json={"deal_id": package["intake"]["deal_id"]}).json()
    response = client.post("/postmortems/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    postmortem_set = session.query(PostmortemSet).filter_by(postmortem_set_id=payload["postmortem_set_id"]).one()
    postmortem_record = session.query(PostmortemRecord).filter_by(postmortem_set_id=payload["postmortem_set_id"]).one()
    findings = session.query(PostmortemFinding).filter_by(postmortem_id=postmortem_record.postmortem_id).all()
    actions = session.query(PostmortemActionItem).filter_by(postmortem_id=postmortem_record.postmortem_id).all()

    assert postmortem_set.deal_closure_report_set_id == report["deal_closure_report_set_id"]
    assert len(findings) >= 1
    assert len(actions) >= 2


def test_build_supplier_rating_and_persist_factors(client, session):
    package = _prepare_r5_final_context(client, session)
    client.post("/deal-closure-reports/build", json={"deal_id": package["intake"]["deal_id"]})
    postmortem = client.post("/postmortems/build", json={"deal_id": package["intake"]["deal_id"]}).json()
    response = client.post("/supplier-ratings/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    rating_set = session.query(SupplierRatingUpdateSet).filter_by(
        supplier_rating_update_set_id=payload["supplier_rating_update_set_id"]
    ).one()
    rating_record = session.query(SupplierRatingUpdateRecord).filter_by(
        supplier_rating_update_set_id=payload["supplier_rating_update_set_id"]
    ).one()
    factors = session.query(SupplierRatingFactor).filter_by(
        supplier_rating_update_id=rating_record.supplier_rating_update_id
    ).all()

    assert rating_set.postmortem_set_id == postmortem["postmortem_set_id"]
    assert rating_set.supplier_id == package["supplier_id"]
    assert len(factors) >= 3


def test_build_knowledge_asset_and_persist_links(client, session):
    package = _prepare_r5_final_context(client, session)
    client.post("/deal-closure-reports/build", json={"deal_id": package["intake"]["deal_id"]})
    postmortem = client.post("/postmortems/build", json={"deal_id": package["intake"]["deal_id"]}).json()
    response = client.post("/knowledge-assets/build", json={"deal_id": package["intake"]["deal_id"]})
    assert response.status_code == 201
    payload = response.json()

    asset_set = session.query(KnowledgeAssetSet).filter_by(
        knowledge_asset_set_id=payload["knowledge_asset_set_id"]
    ).one()
    asset_record = session.query(KnowledgeAssetRecord).filter_by(
        knowledge_asset_set_id=payload["knowledge_asset_set_id"]
    ).one()
    links = session.query(KnowledgeAssetLink).filter_by(knowledge_asset_id=asset_record.knowledge_asset_id).all()

    assert asset_set.postmortem_set_id == postmortem["postmortem_set_id"]
    assert asset_set.archive_export_set_id == package["archive"]["archive_export_set_id"]
    assert asset_set.dashboard_snapshot_set_id == package["dashboard"]["dashboard_snapshot_set_id"]
    assert len(links) >= 3


def test_recovery_r5_cross_module_lifecycle_chain_and_event_continuity(client, session):
    package = _prepare_r5_final_context(client, session)
    deal_id = package["intake"]["deal_id"]
    report = client.post("/deal-closure-reports/build", json={"deal_id": deal_id}).json()
    postmortem = client.post("/postmortems/build", json={"deal_id": deal_id}).json()
    rating = client.post("/supplier-ratings/build", json={"deal_id": deal_id}).json()
    asset = client.post("/knowledge-assets/build", json={"deal_id": deal_id}).json()

    assert package["comparison"]["quote_comparison_set_id"]
    assert package["supplier_contract"]["supplier_contract_set_id"]
    assert package["execution_plan"]["execution_plan_set_id"]
    assert package["purchase_order"]["purchase_order_set_id"]
    assert package["execution"]["execution_command_set_id"]
    assert package["canonical_progress"]["supplier_progress_set_id"]
    assert package["logistics"]["logistics_tracking_set_id"]
    assert package["incident_register"]["incident_register_set_id"]
    assert package["acceptance"]["acceptance_control_set_id"]
    assert package["closing_docs"]["closing_docs_set_id"]
    assert package["payment_tracking"]["payment_tracking_set_id"]
    assert package["claim"]["claim_trigger_set_id"]
    assert report["deal_closure_report_set_id"]
    assert postmortem["postmortem_set_id"]
    assert rating["supplier_rating_update_set_id"]
    assert asset["knowledge_asset_set_id"]

    event_codes = {event.event_code for event in session.query(EventRecord).filter_by(deal_id=deal_id).all()}
    assert "quote_comparison_built" in event_codes
    assert "supplier_contract_built" in event_codes
    assert "execution_plan_built" in event_codes
    assert "purchase_order_built" in event_codes
    assert "delivery_launch_started" in event_codes
    assert "execution_command_built" in event_codes
    assert "supplier_fulfillment_event_recorded" in event_codes
    assert "logistics_tracking_built" in event_codes
    assert "incident_register_built" in event_codes
    assert "acceptance_control_built" in event_codes
    assert "closing_docs_built" in event_codes
    assert "payment_tracking_built" in event_codes
    assert "claim_trigger_built" in event_codes
    assert "deal_closure_report_record_created" in event_codes
    assert "postmortem_record_created" in event_codes
    assert "supplier_rating_record_created" in event_codes
    assert "knowledge_asset_record_created" in event_codes


def test_recovery_r5_reruns_are_append_only_and_queryable(client, session):
    package = _prepare_r5_final_context(client, session)
    deal_id = package["intake"]["deal_id"]

    first_report = client.post("/deal-closure-reports/build", json={"deal_id": deal_id}).json()
    second_report = client.post("/deal-closure-reports/build", json={"deal_id": deal_id}).json()
    first_postmortem = client.post("/postmortems/build", json={"deal_id": deal_id}).json()
    second_postmortem = client.post("/postmortems/build", json={"deal_id": deal_id}).json()
    first_rating = client.post("/supplier-ratings/build", json={"deal_id": deal_id}).json()
    second_rating = client.post("/supplier-ratings/build", json={"deal_id": deal_id}).json()
    first_asset = client.post("/knowledge-assets/build", json={"deal_id": deal_id}).json()
    second_asset = client.post("/knowledge-assets/build", json={"deal_id": deal_id}).json()

    assert first_report["deal_closure_report_set_id"] != second_report["deal_closure_report_set_id"]
    assert first_postmortem["postmortem_set_id"] != second_postmortem["postmortem_set_id"]
    assert first_rating["supplier_rating_update_set_id"] != second_rating["supplier_rating_update_set_id"]
    assert first_asset["knowledge_asset_set_id"] != second_asset["knowledge_asset_set_id"]

    assert len(client.get("/deal-closure-reports", params={"deal_id": deal_id}).json()) >= 2
    assert len(client.get("/postmortems", params={"deal_id": deal_id}).json()) >= 2
    assert len(client.get("/supplier-ratings", params={"deal_id": deal_id}).json()) >= 2
    assert len(client.get("/knowledge-assets", params={"deal_id": deal_id}).json()) >= 2
