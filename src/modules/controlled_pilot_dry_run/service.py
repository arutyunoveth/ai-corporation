import json
from pathlib import Path
from typing import Callable

from sqlalchemy.orm import Session

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
from src.modules.commercial_operator_console.schemas import CommercialOperatorActionRequest
from src.modules.commercial_operator_console.service import record_operator_action
from src.modules.commercial_prebid_demo.schemas import RunCommercialPreBidDemoRequest
from src.modules.commercial_prebid_demo.service import (
    load_commercial_prebid_fixture,
    run_commercial_prebid_demo,
)
from src.modules.controlled_pilot_dry_run.schemas import (
    ControlledPilotDryRunScenarioResult,
    ControlledPilotDryRunSummary,
)
from src.modules.pilot_evidence.service import build_pilot_evidence_record, write_pilot_evidence_bundle
from src.shared.db.base import utcnow
from src.shared.enums import ApprovalDecision


def _manual_suppliers() -> list[ManualSupplierQuoteInput]:
    return [
        ManualSupplierQuoteInput(
            legal_name='OOO "Dry Run Supply 1"',
            display_name="Dry Run Supply 1",
            inn="7704000001",
            country_code="RU",
            contact_name="Anna Dry Run",
            contact_email="anna.dryrun@example.test",
            quoted_amount=1490000,
            currency_code="RUB",
        ),
        ManualSupplierQuoteInput(
            legal_name='OOO "Dry Run Supply 2"',
            display_name="Dry Run Supply 2",
            inn="7704000002",
            country_code="RU",
            contact_name="Boris Dry Run",
            contact_email="boris.dryrun@example.test",
            quoted_amount=1535000,
            currency_code="RUB",
        ),
    ]


def _write_output_bundle(output_dir: Path, prebid, workspace, summary_payload: dict) -> dict[str, str]:
    refs = {
        "prebid_report_markdown": str(output_dir / f"{prebid.deal_id}_prebid_report.md"),
        "prebid_report_json": str(output_dir / f"{prebid.deal_id}_prebid_report.json"),
        "summary_json": str(output_dir / f"{prebid.deal_id}_summary.json"),
    }
    (output_dir / f"{prebid.deal_id}_prebid_report.md").write_text(prebid.report_markdown, encoding="utf-8")
    (output_dir / f"{prebid.deal_id}_prebid_report.json").write_text(
        json.dumps(prebid.report_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    if workspace is not None:
        refs["workspace_report_markdown"] = str(output_dir / f"{prebid.deal_id}_workspace_report.md")
        refs["workspace_report_json"] = str(output_dir / f"{prebid.deal_id}_workspace_report.json")
        (output_dir / f"{prebid.deal_id}_workspace_report.md").write_text(
            workspace.executive_report_markdown,
            encoding="utf-8",
        )
        (output_dir / f"{prebid.deal_id}_workspace_report.json").write_text(
            json.dumps(workspace.executive_report_json, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (output_dir / f"{prebid.deal_id}_summary.json").write_text(
        json.dumps(summary_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return refs


def run_controlled_pilot_scenario(
    session: Session,
    *,
    fixture_name: str,
    output_dir: str | Path,
    provider: str = "stub",
    operator_ref: str = "pilot.operator",
) -> ControlledPilotDryRunScenarioResult:
    fixture = load_commercial_prebid_fixture(fixture_name)
    scenario_id = fixture.get("scenario_id", fixture_name)
    scenario_type = fixture.get("scenario_type", "unknown")
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    started_at = utcnow()

    prebid = run_commercial_prebid_demo(
        session,
        RunCommercialPreBidDemoRequest(fixture_name=fixture_name, provider=provider),
    )
    workspace = None
    blockers: list[dict] = []
    review_notes = [f"Controlled pilot dry run executed for {scenario_id} in {prebid.analysis_mode} mode."]
    final_outcome = "analysis_completed"
    status = "completed"
    submission_readiness_status = None

    if scenario_type == "no_go_tender":
        record_operator_action(
            session,
            prebid.deal_id,
            CommercialOperatorActionRequest(
                action="rejected",
                operator_ref=operator_ref,
                rationale="Scenario stays blocked after controlled review; no commercial progression allowed.",
            ),
        )
        blockers.append({"severity": "high", "summary": "Scenario was rejected during controlled review."})
        review_notes.append("No-go scenario intentionally stopped before TKP/economics handling.")
        final_outcome = "rejected_after_analysis"
        status = "blocked_for_review"
    elif scenario_type == "risky_tender":
        record_operator_action(
            session,
            prebid.deal_id,
            CommercialOperatorActionRequest(
                action="needs_more_review",
                operator_ref=operator_ref,
                rationale="Contract/legal risk requires additional human review before commercial progression.",
            ),
        )
        blockers.append({"severity": "medium", "summary": "Manual review is required before TKP/economics progression."})
        review_notes.append("Risky scenario was held at the operator review gate.")
        final_outcome = "held_for_manual_review"
        status = "blocked_for_review"
    else:
        record_operator_action(
            session,
            prebid.deal_id,
            CommercialOperatorActionRequest(
                action="collect_tkp",
                operator_ref=operator_ref,
                rationale="Controlled pilot dry run is progressing into manual TKP/economics review.",
            ),
        )
        build_supplier_request_draft(
            session,
            prebid.deal_id,
            BuildCommercialSupplierRequestDraftRequest(operator_ref=operator_ref),
        )
        record_commercial_workspace_action(
            session,
            prebid.deal_id,
            CommercialBidWorkspaceActionRequest(
                action="tkp_needed",
                operator_ref=operator_ref,
                rationale="Manual supplier pricing inputs are required for pilot validation.",
            ),
        )
        register_manual_tkp_batch(
            session,
            prebid.deal_id,
            RegisterCommercialTKPBatchRequest(operator_ref=operator_ref, suppliers=_manual_suppliers()),
        )
        record_commercial_workspace_action(
            session,
            prebid.deal_id,
            CommercialBidWorkspaceActionRequest(
                action="tkp_received",
                operator_ref=operator_ref,
                rationale="Manual supplier quote inputs were registered for pilot validation.",
            ),
        )
        workspace = build_commercial_bid_readiness(
            session,
            prebid.deal_id,
            BuildCommercialBidReadinessRequest(operator_ref=operator_ref),
        )
        record_commercial_workspace_action(
            session,
            prebid.deal_id,
            CommercialBidWorkspaceActionRequest(
                action="economics_reviewed",
                operator_ref=operator_ref,
                rationale="Economics and readiness package reviewed in manual-control mode.",
            ),
        )
        ready_action = record_commercial_workspace_action(
            session,
            prebid.deal_id,
            CommercialBidWorkspaceActionRequest(
                action="ready_for_human_submission",
                operator_ref=operator_ref,
                rationale="Dry run completed; any external handling remains manual and outside the repository.",
                approval_decision=ApprovalDecision.GO_WITH_CONDITIONS,
                conditions=["Manual human-controlled submission only outside this repository."],
            ),
        )
        submission_readiness_status = ready_action.submission_readiness_status
        review_notes.append("Commercial readiness path completed without external actions.")
        final_outcome = "internal_ready_for_human_submission_review"

    ended_at = utcnow()
    summary_payload = {
        "fixture_name": fixture_name,
        "scenario_id": scenario_id,
        "deal_id": prebid.deal_id,
        "analysis_mode": prebid.analysis_mode,
        "final_outcome": final_outcome,
        "status": status,
        "submission_readiness_status": submission_readiness_status,
        "blocker_count": len(blockers),
    }
    refs = _write_output_bundle(target_dir, prebid, workspace, summary_payload)
    evidence = build_pilot_evidence_record(
        session,
        scenario_id=scenario_id,
        fixture_name=fixture_name,
        deal_id=prebid.deal_id,
        provider_mode=prebid.analysis_mode,
        started_at=started_at,
        ended_at=ended_at,
        generated_report_refs=refs,
        review_notes=review_notes,
        blockers=blockers,
        customer_usefulness_score=4 if not blockers else 3,
        estimated_time_saved_minutes=90 if workspace is not None else 45,
        final_outcome=final_outcome,
    )
    evidence_json_path, evidence_markdown_path = write_pilot_evidence_bundle(target_dir, evidence)

    return ControlledPilotDryRunScenarioResult(
        fixture_name=fixture_name,
        scenario_id=scenario_id,
        deal_id=prebid.deal_id,
        provider_mode=prebid.analysis_mode,
        status=status,
        final_outcome=final_outcome,
        generated_report_refs=refs,
        evidence_json_path=str(evidence_json_path),
        evidence_markdown_path=str(evidence_markdown_path),
        blocker_count=len(blockers),
    )


def render_controlled_pilot_dry_run_summary(summary: ControlledPilotDryRunSummary) -> str:
    scenario_lines = "\n".join(
        f"- {item.scenario_id} / {item.fixture_name}: {item.status}, outcome={item.final_outcome}, blockers={item.blocker_count}"
        for item in summary.scenario_results
    ) or "- none"
    return (
        "# Controlled Pilot Dry Run Result\n\n"
        f"- Started at (UTC): {summary.started_at.isoformat()}\n"
        f"- Ended at (UTC): {summary.ended_at.isoformat()}\n"
        f"- Provider mode: {summary.provider_mode}\n"
        f"- Completed scenarios: {summary.completed_scenarios}\n"
        f"- Blocked scenarios: {summary.blocked_scenarios}\n\n"
        "## Scenario Results\n"
        f"{scenario_lines}\n"
    )


def write_controlled_pilot_dry_run_summary(
    output_dir: str | Path,
    summary: ControlledPilotDryRunSummary,
) -> tuple[Path, Path]:
    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    json_path = target_dir / "controlled_pilot_dry_run_summary.json"
    markdown_path = target_dir / "controlled_pilot_dry_run_summary.md"
    json_path.write_text(json.dumps(summary.model_dump(mode="json"), ensure_ascii=False, indent=2), encoding="utf-8")
    markdown_path.write_text(render_controlled_pilot_dry_run_summary(summary), encoding="utf-8")
    return json_path, markdown_path


def run_controlled_pilot_dry_run(
    session_factory: Callable[[], Session],
    *,
    fixture_names: list[str],
    output_dir: str | Path,
    provider: str = "stub",
    operator_ref: str = "pilot.operator",
) -> ControlledPilotDryRunSummary:
    started_at = utcnow()
    results: list[ControlledPilotDryRunScenarioResult] = []
    base_dir = Path(output_dir)
    base_dir.mkdir(parents=True, exist_ok=True)

    for fixture_name in fixture_names:
        with session_factory() as session:
            results.append(
                run_controlled_pilot_scenario(
                    session,
                    fixture_name=fixture_name,
                    output_dir=base_dir / fixture_name,
                    provider=provider,
                    operator_ref=operator_ref,
                )
            )

    ended_at = utcnow()
    summary = ControlledPilotDryRunSummary(
        started_at=started_at,
        ended_at=ended_at,
        provider_mode=provider,
        scenario_results=results,
        completed_scenarios=sum(1 for item in results if item.status == "completed"),
        blocked_scenarios=sum(1 for item in results if item.status != "completed"),
    )
    write_controlled_pilot_dry_run_summary(base_dir, summary)
    return summary
