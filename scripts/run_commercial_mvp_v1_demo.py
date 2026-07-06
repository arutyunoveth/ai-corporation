#!/usr/bin/env python3

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.modules.commercial_bid_readiness.schemas import (
    BuildCommercialBidReadinessRequest,
    BuildCommercialSupplierRequestDraftRequest,
    CommercialBidWorkspaceActionRequest,
    RegisterCommercialTKPBatchRequest,
    ManualSupplierQuoteInput,
)
from src.modules.commercial_bid_readiness.service import (
    build_commercial_bid_readiness,
    build_supplier_request_draft,
    record_commercial_workspace_action,
    register_manual_tkp_batch,
)
from src.modules.commercial_prebid_demo.schemas import RunCommercialPreBidDemoRequest
from src.modules.commercial_prebid_demo.service import run_commercial_prebid_demo
from src.modules.pilot_evidence.service import build_pilot_evidence_record, write_pilot_evidence_bundle
from src.shared.db.base import utcnow
from src.shared.db.session import SessionLocal
from src.shared.enums import ApprovalDecision


def _manual_suppliers() -> list[ManualSupplierQuoteInput]:
    return [
        ManualSupplierQuoteInput(
            legal_name='OOO "Electro Supply 1"',
            display_name="Electro Supply 1",
            inn="7701000001",
            country_code="RU",
            contact_name="Anna Supplier",
            contact_email="anna@example.test",
            tags=["ELECTRICAL_EQUIPMENT"],
            quoted_amount=1480000,
            currency_code="RUB",
            notes="Primary commercial option.",
        ),
        ManualSupplierQuoteInput(
            legal_name='OOO "Electro Supply 2"',
            display_name="Electro Supply 2",
            inn="7701000002",
            country_code="RU",
            contact_name="Boris Supplier",
            contact_email="boris@example.test",
            tags=["ELECTRICAL_EQUIPMENT"],
            quoted_amount=1525000,
            currency_code="RUB",
            notes="Fallback commercial option.",
        ),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the bounded Commercial MVP v1 demo workflow.")
    parser.add_argument("--fixture", default="commercial_mvp_demo")
    parser.add_argument("--provider", default="stub", choices=["deterministic", "stub", "llm"])
    parser.add_argument("--output-dir", default="tmp/commercial_mvp_v1_demo")
    parser.add_argument("--operator-ref", default="commercial.operator")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    started_at = utcnow()

    with SessionLocal() as session:
        prebid = run_commercial_prebid_demo(
            session,
            RunCommercialPreBidDemoRequest(
                fixture_name=args.fixture,
                provider=args.provider,
            ),
        )
        supplier_request = build_supplier_request_draft(
            session,
            prebid.deal_id,
            BuildCommercialSupplierRequestDraftRequest(operator_ref=args.operator_ref),
        )
        tkp_batch = register_manual_tkp_batch(
            session,
            prebid.deal_id,
            RegisterCommercialTKPBatchRequest(
                operator_ref=args.operator_ref,
                suppliers=_manual_suppliers(),
            ),
        )
        workspace = build_commercial_bid_readiness(
            session,
            prebid.deal_id,
            BuildCommercialBidReadinessRequest(operator_ref=args.operator_ref),
        )
        ready_action = record_commercial_workspace_action(
            session,
            prebid.deal_id,
            CommercialBidWorkspaceActionRequest(
                action="ready_for_human_submission",
                operator_ref=args.operator_ref,
                rationale="Internal checks are complete; keep final submission human-controlled.",
                approval_decision=ApprovalDecision.GO_WITH_CONDITIONS,
                conditions=["Manual submission only after final operator review."],
            ),
        )
        ended_at = utcnow()
        report_refs = {
            "prebid_report_markdown": str(output_dir / f"{prebid.deal_id}_prebid_report.md"),
            "prebid_report_json": str(output_dir / f"{prebid.deal_id}_prebid_report.json"),
            "workspace_report_markdown": str(output_dir / f"{prebid.deal_id}_workspace_report.md"),
            "workspace_report_json": str(output_dir / f"{prebid.deal_id}_workspace_report.json"),
            "summary_json": str(output_dir / f"{prebid.deal_id}_summary.json"),
        }
        evidence = build_pilot_evidence_record(
            session,
            scenario_id=prebid.report_json.get("scenario_id", args.fixture),
            fixture_name=prebid.fixture_name,
            deal_id=prebid.deal_id,
            provider_mode=prebid.analysis_mode,
            started_at=started_at,
            ended_at=ended_at,
            generated_report_refs=report_refs,
            review_notes=[
                "Controlled commercial pilot rehearsal executed in internal-only mode.",
                "Final outcome remains human-reviewed and external execution stays out of scope.",
            ],
            blockers=[],
            customer_usefulness_score=4,
            estimated_time_saved_minutes=90,
            final_outcome="internal_ready_for_human_submission_review",
        )

    (output_dir / f"{prebid.deal_id}_prebid_report.md").write_text(prebid.report_markdown, encoding="utf-8")
    (output_dir / f"{prebid.deal_id}_prebid_report.json").write_text(
        json.dumps(prebid.report_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{prebid.deal_id}_workspace_report.md").write_text(
        workspace.executive_report_markdown,
        encoding="utf-8",
    )
    (output_dir / f"{prebid.deal_id}_workspace_report.json").write_text(
        json.dumps(workspace.executive_report_json, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (output_dir / f"{prebid.deal_id}_summary.json").write_text(
        json.dumps(
            {
                "deal_id": prebid.deal_id,
                "scenario_id": prebid.report_json.get("scenario_id", args.fixture),
                "analysis_mode": prebid.analysis_mode,
                "supplier_request_subject": supplier_request.request_subject,
                "quote_set_id": tkp_batch.quote_set_id,
                "submission_readiness_set_id": ready_action.submission_readiness_set_id,
                "submission_readiness_status": ready_action.submission_readiness_status,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    write_pilot_evidence_bundle(output_dir, evidence)

    print(output_dir)


if __name__ == "__main__":
    main()
