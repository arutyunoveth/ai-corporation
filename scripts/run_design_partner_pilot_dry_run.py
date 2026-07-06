#!/usr/bin/env python3

import json
import sys
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.modules.partner_export.service import (
    approve_for_delivery,
    generate_export_package,
    mark_delivered_manually,
    render_export_json,
    render_export_markdown,
)
from src.modules.partner_workspace.schemas import IntakeSourceType, RedactionStatus
from src.modules.partner_workspace.service import (
    add_intake_record,
    approve_for_pilot_use,
    create_workspace,
    mark_redacted_for_partner,
)
from src.modules.pilot_feedback.schemas import FeedbackSource, FeedbackType, FinalDecision, NextAction
from src.modules.pilot_feedback.service import create_feedback, create_outcome
from src.modules.pilot_access_boundary.schemas import VisibilityLevel


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Run the design-partner pilot dry run.")
    parser.add_argument("--output-dir", default="tmp/design_partner_pilot_dry_run")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Design-Partner Pilot Dry Run ===")
    print(f"Output dir: {output_dir}")
    print()

    # Step 1: Create workspace
    ws = create_workspace(
        partner_label="DP-Dry-Run-001",
        created_by="dp.dry.run.operator",
        data_handling_notes="Synthetic dry-run data only. No real partner data.",
    )
    print(f"[1] Workspace created: {ws.partner_workspace_id}")

    # Step 2: Create intake records
    clean_record = add_intake_record(
        partner_workspace_id=ws.partner_workspace_id,
        source_type=IntakeSourceType.notice_text,
        source_label="Tender notice (synthetic)",
        redaction_status=RedactionStatus.not_required,
        visibility_level=VisibilityLevel.partner_visible,
    )
    print(f"[2a] Clean intake record: {clean_record.intake_record_id}")

    sensitive_record = add_intake_record(
        partner_workspace_id=ws.partner_workspace_id,
        source_type=IntakeSourceType.contract_draft_text,
        source_label="Contract draft (synthetic, sensitive)",
        contains_sensitive_data=True,
        redaction_status=RedactionStatus.raw_received,
        visibility_level=VisibilityLevel.operator_visible,
    )
    print(f"[2b] Sensitive intake record: {sensitive_record.intake_record_id}")

    # Step 3: Apply redaction workflow
    redacted_record = mark_redacted_for_partner(sensitive_record)
    print(f"[3a] Redacted for partner: {redacted_record.redaction_status.value}")

    approved_record = approve_for_pilot_use(clean_record)
    print(f"[3b] Approved for pilot: {approved_record.redaction_status.value}")

    # Step 4: Prepare report sections
    report_sections = {
        "customer_report": f"# Pre-Bid Report\n\nDeal: SC-DRY-001\n\n## Requirements\n- Requirement 1\n- Requirement 2\n\n## Risks\n- Low risk item\n\n## Recommendation\nProceed with manual review.",
        "summary": "Partner-safe executive summary for dry run.",
        "metrics": "Metrics: 3 requirements identified, 1 risk flagged.",
        "runtime_trace": "DEBUG: trace data - internal only",
        "sensitive_legal_note": "INTERNAL: legal review notes - restricted",
        "operator_decision": "Operator approved analysis on 2026-06-06",
    }
    print("[4] Report sections prepared")

    # Step 5: Generate export package
    package = generate_export_package(
        partner_workspace_id=ws.partner_workspace_id,
        scenario_or_tender_id="SC-DRY-001",
        report_sections=report_sections,
        intake_records=[approved_record, redacted_record],
    )
    print(f"[5] Export package: {package.export_package_id}")
    print(f"    Status: {package.export_status.value}")
    print(f"    Summary: {package.export_summary}")
    print(f"    Included: {package.included_sections}")
    print(f"    Redacted: {package.redacted_sections}")
    print(f"    Blocked: {package.blocked_sections}")

    # Step 6: Export outputs
    md_content = render_export_markdown(package)
    json_content = render_export_json(package)

    md_path = output_dir / f"{package.export_package_id}_export_package.md"
    json_path = output_dir / f"{package.export_package_id}_export_package.json"
    md_path.write_text(md_content, encoding="utf-8")
    json_path.write_text(json.dumps(json_content, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[6a] Markdown package: {md_path}")
    print(f"[6b] JSON package: {json_path}")

    # Step 7: Approve and mark delivered
    approved = approve_for_delivery(package)
    print(f"[7a] Approved for delivery: {approved.export_status.value}")

    delivered = mark_delivered_manually(approved)
    print(f"[7b] Marked delivered manually: {delivered.export_status.value}")

    # Step 8: Record feedback
    feedback = create_feedback(
        partner_workspace_id=ws.partner_workspace_id,
        export_package_id_or_pilot_run_id=package.export_package_id,
        feedback_source=FeedbackSource.internal_review,
        feedback_type=FeedbackType.positive,
        usefulness_score=4,
        clarity_score=4,
        trust_score=4,
        would_pay_signal=True,
        operator_notes="Dry run completed successfully. All boundaries respected.",
        next_action=NextAction.prepare_paid_pilot_offer,
    )
    print(f"[8] Feedback recorded: {feedback.feedback_id}")

    # Step 9: Record outcome
    outcome = create_outcome(
        partner_workspace_id=ws.partner_workspace_id,
        pilot_run_id=package.export_package_id,
        final_decision=FinalDecision.continue_design_partner,
        decision_reason="Dry run completed with all access boundaries respected.",
        conversion_readiness="medium",
        recommended_next_step="Prepare for real design-partner pilot cycle.",
    )
    print(f"[9] Outcome recorded: {outcome.outcome_id}")

    # Step 10: Write dry-run summary
    summary = {
        "workspace_id": ws.partner_workspace_id,
        "export_package_id": package.export_package_id,
        "feedback_id": feedback.feedback_id,
        "outcome_id": outcome.outcome_id,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "included_sections": package.included_sections,
        "redacted_sections": package.redacted_sections,
        "blocked_sections": package.blocked_sections,
        "export_status": package.export_status.value,
        "delivery_status": delivered.export_status.value,
        "restricted_sensitive_blocked": "sensitive_legal_note" in package.blocked_sections,
        "internal_only_redacted": "runtime_trace" in package.redacted_sections,
        "operator_visible_redacted": "operator_decision" in package.redacted_sections,
        "customer_report_included": "customer_report" in package.included_sections,
    }
    summary_path = output_dir / "dry_run_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[10] Dry-run summary: {summary_path}")
    print()
    print("=== Dry Run Complete ===")
    print(output_dir)


if __name__ == "__main__":
    main()
