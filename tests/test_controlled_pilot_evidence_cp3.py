import json

from src.modules.commercial_bid_readiness.schemas import (
    BuildCommercialBidReadinessRequest,
    BuildCommercialSupplierRequestDraftRequest,
    CommercialBidWorkspaceActionRequest,
    ManualSupplierQuoteInput,
    RegisterCommercialTKPBatchRequest,
)
from src.modules.commercial_bid_readiness.service import (
    build_commercial_bid_readiness,
    build_supplier_request_draft,
    record_commercial_workspace_action,
    register_manual_tkp_batch,
)
from src.modules.commercial_prebid_demo.schemas import RunCommercialPreBidDemoRequest
from src.modules.commercial_prebid_demo.service import run_commercial_prebid_demo
from src.modules.pilot_evidence.service import (
    build_pilot_evidence_record,
    render_pilot_evidence_markdown,
    write_pilot_evidence_bundle,
)
from src.shared.db.base import utcnow
from src.shared.enums import ApprovalDecision


def _manual_suppliers() -> list[ManualSupplierQuoteInput]:
    return [
        ManualSupplierQuoteInput(
            legal_name='OOO "Pilot Evidence 1"',
            display_name="Pilot Evidence 1",
            inn="7703000001",
            country_code="RU",
            contact_name="Anna Evidence",
            contact_email="anna.evidence@example.test",
            quoted_amount=1475000,
            currency_code="RUB",
        ),
        ManualSupplierQuoteInput(
            legal_name='OOO "Pilot Evidence 2"',
            display_name="Pilot Evidence 2",
            inn="7703000002",
            country_code="RU",
            contact_name="Boris Evidence",
            contact_email="boris.evidence@example.test",
            quoted_amount=1510000,
            currency_code="RUB",
        ),
    ]


def test_pilot_evidence_bundle_captures_controlled_run(session, tmp_path):
    started_at = utcnow()
    prebid = run_commercial_prebid_demo(
        session,
        RunCommercialPreBidDemoRequest(
            fixture_name="controlled_pilot_tkp_economics",
            provider="stub",
        ),
    )
    build_supplier_request_draft(
        session,
        prebid.deal_id,
        BuildCommercialSupplierRequestDraftRequest(operator_ref="pilot.operator"),
    )
    register_manual_tkp_batch(
        session,
        prebid.deal_id,
        RegisterCommercialTKPBatchRequest(
            operator_ref="pilot.operator",
            suppliers=_manual_suppliers(),
        ),
    )
    build_commercial_bid_readiness(
        session,
        prebid.deal_id,
        BuildCommercialBidReadinessRequest(operator_ref="pilot.operator"),
    )
    record_commercial_workspace_action(
        session,
        prebid.deal_id,
        CommercialBidWorkspaceActionRequest(
            action="ready_for_human_submission",
            operator_ref="pilot.operator",
            rationale="Controlled pilot evidence path complete; external handling remains manual.",
            approval_decision=ApprovalDecision.GO_WITH_CONDITIONS,
            conditions=["Manual human-controlled handling only outside this repository."],
        ),
    )
    ended_at = utcnow()

    refs = {
        "prebid_report_json": str(tmp_path / f"{prebid.deal_id}_prebid_report.json"),
        "workspace_report_json": str(tmp_path / f"{prebid.deal_id}_workspace_report.json"),
        "summary_json": str(tmp_path / f"{prebid.deal_id}_summary.json"),
    }
    evidence = build_pilot_evidence_record(
        session,
        scenario_id=prebid.report_json["scenario_id"],
        fixture_name=prebid.fixture_name,
        deal_id=prebid.deal_id,
        provider_mode=prebid.analysis_mode,
        started_at=started_at,
        ended_at=ended_at,
        generated_report_refs=refs,
        review_notes=["Operator completed the rehearsal without external actions."],
        blockers=[],
        customer_usefulness_score=4,
        estimated_time_saved_minutes=75,
        final_outcome="internal_ready_for_human_submission_review",
    )

    assert evidence.scenario_id == "CP-SC-004"
    assert evidence.provider_mode == "llm_controlled_stub"
    assert evidence.metrics.generated_report_count == 3
    assert evidence.metrics.operator_action_count >= 1
    assert evidence.final_outcome == "internal_ready_for_human_submission_review"

    markdown = render_pilot_evidence_markdown(evidence)
    assert "Pilot Evidence Ledger" in markdown
    assert "Final outcome: internal_ready_for_human_submission_review" in markdown
    assert "Generated Report Refs" in markdown

    json_path, markdown_path = write_pilot_evidence_bundle(tmp_path, evidence)
    assert json_path.exists()
    assert markdown_path.exists()

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    assert payload["scenario_id"] == "CP-SC-004"
    assert payload["customer_usefulness_score"] == 4
    assert payload["estimated_time_saved_minutes"] == 75


def test_pilot_evidence_docs_exist_and_keep_scope_bounded():
    ledger_text = open("docs/product/Pilot_Evidence_Ledger.md", encoding="utf-8").read()
    metrics_text = open("docs/product/Pilot_Metrics_Definition.md", encoding="utf-8").read()

    assert "pilot_run_id" in ledger_text
    assert "no production telemetry pipeline" in ledger_text
    assert "no live telemetry" in metrics_text
    assert "no auto-export to customer systems" in metrics_text
