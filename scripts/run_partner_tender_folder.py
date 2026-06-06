#!/usr/bin/env python3
"""
Run a real (or synthetic) partner tender from a local folder.

Usage:
    .venv/bin/python scripts/run_partner_tender_folder.py \
        --partner-id partner_001 \
        --tender-dir local_pilot_runs/partner_001/tender_001 \
        --provider stub \
        --output-dir local_pilot_runs/partner_001/tender_001/04_system_output
"""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

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
    check_export_readiness,
    classify_default_visibility,
    create_workspace,
    generate_redaction_checklist,
    mark_redacted_for_partner,
    require_redaction,
)
from src.modules.pilot_access_boundary.schemas import VisibilityLevel
from src.modules.pilot_feedback.schemas import FeedbackSource, FeedbackType, FinalDecision, NextAction
from src.modules.pilot_feedback.service import create_feedback, create_outcome


def _validate_tender_dir(tender_dir: Path) -> None:
    """Validate the tender folder structure exists and has required files."""
    if not tender_dir.is_dir():
        print(f"ERROR: Tender directory does not exist: {tender_dir}")
        sys.exit(1)

    extracted_dir = tender_dir / "02_extracted_text"
    if not extracted_dir.is_dir():
        print(f"ERROR: Missing '02_extracted_text/' subdirectory in {tender_dir}")
        print("Create the folder structure:")
        print(f"  mkdir -p {tender_dir}/02_extracted_text")
        print(f"  mkdir -p {tender_dir}/01_raw_docs")
        print(f"  mkdir -p {tender_dir}/03_operator_notes")
        print(f"  mkdir -p {tender_dir}/04_system_output")
        print(f"  mkdir -p {tender_dir}/05_partner_export")
        print(f"  mkdir -p {tender_dir}/06_feedback")
        sys.exit(1)

    required = ["notice.txt", "technical_spec.txt", "contract_draft.txt"]
    missing = [f for f in required if not (extracted_dir / f).is_file()]
    if missing:
        print(f"ERROR: Missing required extracted text files in {extracted_dir}:")
        for f in missing:
            print(f"  - {f}")
        print("Extract text from original documents and save as plain text files.")
        sys.exit(1)


def _ensure_output_dirs(output_dir: Path, export_dir: Path) -> None:
    """Create output directories if they don't exist."""
    output_dir.mkdir(parents=True, exist_ok=True)
    export_dir.mkdir(parents=True, exist_ok=True)


def _read_text_file(path: Path) -> str:
    """Read a text file and return its contents."""
    return path.read_text(encoding="utf-8")


def _read_partner_profile(partner_dir: Path) -> dict[str, Any]:
    """Read partner_profile.md if it exists, returning a summary dict."""
    profile_path = partner_dir / "partner_profile.md"
    if profile_path.is_file():
        text = profile_path.read_text(encoding="utf-8")
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        return {
            "found": True,
            "line_count": len(lines),
            "preview": " ".join(lines[:5])[:200],
        }
    return {"found": False, "line_count": 0, "preview": ""}


def _run_stub_analysis(
    notice_text: str,
    technical_spec_text: str,
    contract_draft_text: str,
) -> dict[str, Any]:
    """Run stub analysis on the extracted text files."""
    return {
        "tender_summary": f"Tender notice: {notice_text[:100]}...",
        "technical_requirements": [
            "Requirement based on technical specification",
            "Compliance with stated standards required",
            "Delivery schedule must be confirmed",
        ],
        "participant_requirements": [
            "Valid business registration",
            "Relevant industry certifications",
            "Proof of prior similar work",
        ],
        "required_documents": [
            "Company registration certificate",
            "Tax clearance certificate",
            "Technical proposal",
            "Financial statements",
        ],
        "contract_risks": [
            "Review payment terms in contract draft",
            "Verify liability and indemnification clauses",
            "Check termination conditions",
        ],
        "preliminary_recommendation": "GO_WITH_CONDITIONS",
        "analysis_mode": "stub",
    }


def _try_llm_analysis(
    notice_text: str,
    technical_spec_text: str,
    contract_draft_text: str,
) -> dict[str, Any] | None:
    """Try to run a controlled LLM pre-bid analysis.

    Requires a DB session and API key. Returns None if unavailable.
    """
    try:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import Session

        from src.shared.config.settings import get_settings

        settings = get_settings()
        if not settings.database_url:
            return None

        engine = create_engine(settings.database_url)
        with Session(engine) as session:
            from src.modules.controlled_llm_prebid.service import run_controlled_llm_prebid_analysis

            llm_context = {
                "deal_id": f"PP1-{datetime.now(UTC).strftime('%Y%m%d')}",
                "title": notice_text[:200],
                "customer_name": "Partner",
                "participant_requirements": [
                    "Valid business registration",
                    "Relevant industry certifications",
                ],
                "required_documents": [
                    "Company registration certificate",
                    "Tax clearance certificate",
                ],
                "contract_risks": [
                    "Review payment terms",
                    "Check termination conditions",
                ],
            }
            result = run_controlled_llm_prebid_analysis(
                session,
                provider_mode="llm",
                context=llm_context,
            )
            return {
                "analysis_mode": result.analysis_mode,
                "overall_review_status": result.overall_review_status,
                "sections": {
                    k: {
                        "validation_status": v.get("validation_status"),
                        "review_status": v.get("review_status"),
                        "raw_output": v.get("raw_output"),
                    }
                    for k, v in result.sections.items()
                },
                "trace_ids": result.trace_ids,
            }
    except Exception as exc:
        print(f"WARNING: LLM analysis unavailable, falling back to stub: {exc}")
        return None


def _build_internal_analysis_markdown(
    analysis: dict[str, Any],
    notice_text: str,
    technical_spec_text: str,
    contract_draft_text: str,
    partner_profile: dict[str, Any],
    records: list[dict[str, Any]],
) -> str:
    """Build a full internal analysis markdown report."""
    lines: list[str] = [
        "# Internal Analysis Report",
        "",
        f"**Generated**: {datetime.now(UTC).isoformat()}",
        f"**Analysis Mode**: {analysis.get('analysis_mode', 'stub')}",
        "",
        "---",
        "## Partner Profile",
        "",
    ]
    if partner_profile["found"]:
        lines.append(f"Profile found: {partner_profile['preview']}")
    else:
        lines.append("No partner profile found.")

    lines += [
        "",
        "---",
        "## Source Documents",
        "",
        f"- Notice: {len(notice_text)} chars",
        f"- Technical Spec: {len(technical_spec_text)} chars",
        f"- Contract Draft: {len(contract_draft_text)} chars",
        "",
        "---",
        "## Tender Summary",
        "",
        analysis.get("tender_summary", "No summary generated"),
        "",
    ]

    reqs = analysis.get("technical_requirements", [])
    if reqs:
        lines += ["## Technical Requirements", ""]
        lines += [f"- {r}" for r in reqs]
        lines += [""]

    parts = analysis.get("participant_requirements", [])
    if parts:
        lines += ["## Participant Requirements", ""]
        lines += [f"- {p}" for p in parts]
        lines += [""]

    docs = analysis.get("required_documents", [])
    if docs:
        lines += ["## Required Documents", ""]
        lines += [f"- {d}" for d in docs]
        lines += [""]

    risks = analysis.get("contract_risks", [])
    if risks:
        lines += ["## Contract Risks", ""]
        lines += [f"- {r}" for r in risks]
        lines += [""]

    lines += [
        "---",
        "## Preliminary Recommendation",
        "",
        analysis.get("preliminary_recommendation", "No recommendation"),
        "",
    ]

    llm = analysis.get("llm_analysis")
    if llm:
        lines += [
            "---",
            "## Controlled LLM Review",
            "",
            f"- Mode: {llm.get('analysis_mode', 'N/A')}",
            f"- Status: {llm.get('overall_review_status', 'N/A')}",
            "",
            "### Sections",
        ]
        for section_name, section_data in llm.get("sections", {}).items():
            lines.append(f"- **{section_name}**: validation={section_data.get('validation_status')}, review={section_data.get('review_status')}")
        lines += [""]

    lines += [
        "---",
        "## Intake Records",
        "",
    ]
    for r in records:
        lines.append(f"- {r['source_label']}: status={r['redaction_status']}, visibility={r['visibility_level']}")
    lines += [""]

    lines += [
        "---",
        "## Redaction Checklist",
        "",
    ]
    records_data = [r.get("record") for r in records if "record" in r]
    if records_data:
        checklist = generate_redaction_checklist(records_data)
        for item in checklist:
            lines.append(
                f"- {item.get('source_label', item.get('intake_record_id', '?'))}: "
                f"needs_redaction={item.get('needs_redaction', '?')}, "
                f"can_use_in_pilot={item.get('can_use_in_pilot', '?')}, "
                f"can_appear_in_report={item.get('can_appear_in_partner_report', '?')}"
            )
    lines += [""]

    return "\n".join(lines)


def _build_partner_sections(
    analysis: dict[str, Any],
) -> dict[str, str]:
    """Build report sections with varying visibility levels for export."""
    reqs = analysis.get("technical_requirements", [])
    parts = analysis.get("participant_requirements", [])
    risks = analysis.get("contract_risks", [])
    docs = analysis.get("required_documents", [])

    technical_lines = "\n".join(f"- {r}" for r in reqs)
    participant_lines = "\n".join(f"- {p}" for p in parts)
    risk_lines = "\n".join(f"- {r}" for r in risks)
    docs_lines = "\n".join(f"- {d}" for d in docs)

    summary = analysis.get("tender_summary", "No summary available.")
    recommendation = analysis.get("preliminary_recommendation", "No recommendation")

    return {
        "customer_report": (
            f"# Partner Pre-Bid Report\n\n"
            f"## Tender Summary\n{summary}\n\n"
            f"## Technical Requirements\n{technical_lines}\n\n"
            f"## Required Documents\n{docs_lines}\n\n"
            f"## Recommendation\n{recommendation}\n\n"
            f"*Analysis mode: stub | Human review required before bid*\n"
        ),
        "summary": "Partner-safe executive summary of the tender analysis.",
        "detailed_analysis": (
            "## Detailed Analysis\n"
            "The tender has been reviewed against the provided documents.\n"
            f"### Participant Requirements\n{participant_lines}\n"
        ),
        "contract_risks_overview": (
            "## Contract Risks\n"
            f"{risk_lines}\n"
        ),
        "runtime_trace": (
            "DEBUG: trace_id=PP1-internal | This section contains internal processing metadata. "
            "Operator: system | Timestamp: internal"
        ),
        "sensitive_legal_note": (
            "INTERNAL LEGAL REVIEW: This section contains privileged legal analysis. "
            "Not for external distribution."
        ),
        "operator_decision": (
            "Operator decision: Analysis reviewed and approved for partner delivery on "
            f"{datetime.now(UTC).isoformat()}. Requires final human approval."
        ),
    }


def _write_outputs(
    output_dir: Path,
    export_dir: Path,
    *,
    partner_id: str,
    tender_dir: str,
    ws_id: str,
    records: list[dict[str, Any]],
    analysis: dict[str, Any],
    internal_markdown: str,
    package_id: str,
    export_md: str,
    export_json: dict[str, Any],
    delivery_status: str,
) -> dict[str, Any]:
    """Write all output files and return a run summary."""
    summary: dict[str, Any] = {
        "partner_id": partner_id,
        "tender_dir": str(tender_dir),
        "workspace_id": ws_id,
        "export_package_id": package_id,
        "delivery_status": delivery_status,
        "analysis_mode": analysis.get("analysis_mode", "stub"),
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "source_files": {
            "notice_txt": notice_chars if (notice_chars := analysis.get("_notice_chars")) else 0,
            "technical_spec_txt": spec_chars if (spec_chars := analysis.get("_spec_chars")) else 0,
            "contract_draft_txt": contract_chars if (contract_chars := analysis.get("_contract_chars")) else 0,
        },
        "intake_records": [
            {
                "source_label": r["source_label"],
                "source_type": r["source_type"].value if hasattr(r["source_type"], "value") else str(r["source_type"]),
                "redaction_status": r["redaction_status"].value if hasattr(r["redaction_status"], "value") else str(r["redaction_status"]),
                "visibility_level": r["visibility_level"].value if hasattr(r["visibility_level"], "value") else str(r["visibility_level"]),
            }
            for r in records
        ],
        "included_sections": export_json.get("included_sections", []),
        "redacted_sections": export_json.get("redacted_sections", []),
        "blocked_sections": export_json.get("blocked_sections", []),
    }

    summary_path = output_dir / "run_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    internal_path = output_dir / "internal_analysis.md"
    internal_path.write_text(internal_markdown, encoding="utf-8")

    report_path = export_dir / "partner_report.md"
    report_path.write_text(export_md, encoding="utf-8")

    export_summary_path = export_dir / "export_summary.json"
    export_summary_path.write_text(json.dumps(export_json, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  Run summary:       {summary_path}")
    print(f"  Internal analysis:  {internal_path}")
    print(f"  Partner report:     {report_path}")
    print(f"  Export summary:     {export_summary_path}")

    return summary


def _create_export_package_and_deliver(
    ws_id: str,
    partner_sections: dict[str, str],
    intake_records: list,
    tender_label: str,
) -> tuple:
    """Generate export package, approve, and mark delivered."""
    package = generate_export_package(
        partner_workspace_id=ws_id,
        scenario_or_tender_id=tender_label,
        report_sections=partner_sections,
        intake_records=intake_records,
    )
    print(f"  Export package: {package.export_package_id}")
    print(f"  Status: {package.export_status.value}")
    print(f"  Included: {package.included_sections}")
    print(f"  Redacted: {package.redacted_sections}")
    print(f"  Blocked: {package.blocked_sections}")

    if package.export_status.value != "blocked":
        approved = approve_for_delivery(package)
        delivered = mark_delivered_manually(approved)
        print(f"  Approved & marked delivered: {delivered.export_status.value}")
    else:
        print("  WARNING: Export blocked due to restricted sections. Manual review required.")
        delivered = package

    return package, delivered


def _record_feedback_and_outcome(
    ws_id: str,
    package_id: str,
) -> tuple:
    """Record stub feedback and outcome."""
    feedback = create_feedback(
        partner_workspace_id=ws_id,
        export_package_id_or_pilot_run_id=package_id,
        feedback_source=FeedbackSource.internal_review,
        feedback_type=FeedbackType.positive,
        usefulness_score=4,
        clarity_score=4,
        trust_score=4,
        would_pay_signal=None,
        operator_notes="PP1 tender folder run completed. Awaiting real partner feedback.",
        next_action=NextAction.iterate_report,
    )
    print(f"  Feedback recorded: {feedback.feedback_id}")

    outcome = create_outcome(
        partner_workspace_id=ws_id,
        pilot_run_id=package_id,
        final_decision=FinalDecision.continue_design_partner,
        decision_reason="Tender folder processed. Awaiting partner review before further action.",
        conversion_readiness="not_assessed",
        recommended_next_step="Send partner report and collect feedback.",
    )
    print(f"  Outcome recorded: {outcome.outcome_id}")

    return feedback, outcome


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run a real (or synthetic) partner tender from a local folder."
    )
    parser.add_argument(
        "--partner-id",
        required=True,
        help="Partner identifier (e.g., partner_001)",
    )
    parser.add_argument(
        "--tender-dir",
        required=True,
        type=Path,
        help="Path to the tender folder (e.g., local_pilot_runs/partner_001/tender_001)",
    )
    parser.add_argument(
        "--provider",
        required=True,
        choices=["stub", "llm"],
        help="Analysis provider: stub (canned) or llm (requires DB + API key)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Output directory for system analysis (default: <tender-dir>/04_system_output)",
    )
    args = parser.parse_args()

    tender_dir: Path = args.tender_dir.resolve()
    partner_id: str = args.partner_id
    tender_label: str = tender_dir.name
    partner_dir: Path = tender_dir.parent

    if args.output_dir:
        output_dir = args.output_dir.resolve()
    else:
        output_dir = tender_dir / "04_system_output"

    export_dir = tender_dir / "05_partner_export"
    print("=== Partner Tender Folder Runner (PP1) ===")
    print(f"  Partner ID:  {partner_id}")
    print(f"  Tender dir:  {tender_dir}")
    print(f"  Provider:    {args.provider}")
    print(f"  Output dir:  {output_dir}")
    print()

    # Step 1: Validate folder structure
    print("[1] Validating folder structure...")
    _validate_tender_dir(tender_dir)
    _ensure_output_dirs(output_dir, export_dir)
    print("  OK")

    # Step 2: Read partner profile
    print("[2] Reading partner profile...")
    partner_profile = _read_partner_profile(partner_dir)
    if partner_profile["found"]:
        print(f"  Profile found: {partner_profile['line_count']} lines")
    else:
        print("  No partner profile found (optional)")

    # Step 3: Read extracted text files
    print("[3] Reading extracted text files...")
    extracted_dir = tender_dir / "02_extracted_text"
    notice_text = _read_text_file(extracted_dir / "notice.txt")
    technical_spec_text = _read_text_file(extracted_dir / "technical_spec.txt")
    contract_draft_text = _read_text_file(extracted_dir / "contract_draft.txt")
    print(f"  notice.txt:          {len(notice_text)} chars")
    print(f"  technical_spec.txt:  {len(technical_spec_text)} chars")
    print(f"  contract_draft.txt:  {len(contract_draft_text)} chars")

    # Step 4: Create partner workspace
    print("[4] Creating partner workspace...")
    ws = create_workspace(
        partner_label=partner_id,
        created_by="pp1.tender.folder.runner",
        data_handling_notes=f"PP1 run for tender {tender_label}. Stored at {tender_dir}.",
    )
    print(f"  Workspace: {ws.partner_workspace_id}")

    # Step 5: Create intake records for each text source
    print("[5] Creating intake records...")
    records_info = []
    intake_records = []

    notice_record = add_intake_record(
        partner_workspace_id=ws.partner_workspace_id,
        source_type=IntakeSourceType.notice_text,
        source_label=f"notice.txt ({tender_label})",
        contains_sensitive_data=False,
        redaction_status=RedactionStatus.not_required,
    )
    notice_record = approve_for_pilot_use(notice_record)
    records_info.append({
        "source_label": notice_record.source_label,
        "source_type": notice_record.source_type,
        "redaction_status": notice_record.redaction_status,
        "visibility_level": notice_record.visibility_level,
    })
    intake_records.append(notice_record)
    print(f"  Notice record: {notice_record.intake_record_id}")

    spec_record = add_intake_record(
        partner_workspace_id=ws.partner_workspace_id,
        source_type=IntakeSourceType.technical_spec_text,
        source_label=f"technical_spec.txt ({tender_label})",
        contains_sensitive_data=True,
        redaction_status=RedactionStatus.raw_received,
    )
    spec_record = require_redaction(spec_record)
    spec_record = mark_redacted_for_partner(spec_record)
    records_info.append({
        "source_label": spec_record.source_label,
        "source_type": spec_record.source_type,
        "redaction_status": spec_record.redaction_status,
        "visibility_level": spec_record.visibility_level,
    })
    intake_records.append(spec_record)
    print(f"  Tech spec record: {spec_record.intake_record_id} (redacted for partner)")

    contract_record = add_intake_record(
        partner_workspace_id=ws.partner_workspace_id,
        source_type=IntakeSourceType.contract_draft_text,
        source_label=f"contract_draft.txt ({tender_label})",
        contains_sensitive_data=True,
        redaction_status=RedactionStatus.raw_received,
    )
    contract_record = require_redaction(contract_record)
    contract_record = mark_redacted_for_partner(contract_record)
    records_info.append({
        "source_label": contract_record.source_label,
        "source_type": contract_record.source_type,
        "redaction_status": contract_record.redaction_status,
        "visibility_level": contract_record.visibility_level,
    })
    intake_records.append(contract_record)
    print(f"  Contract record: {contract_record.intake_record_id} (redacted for partner)")

    # Step 6: Run analysis
    print(f"[6] Running analysis (provider={args.provider})...")
    analysis = _run_stub_analysis(notice_text, technical_spec_text, contract_draft_text)
    analysis["_notice_chars"] = len(notice_text)
    analysis["_spec_chars"] = len(technical_spec_text)
    analysis["_contract_chars"] = len(contract_draft_text)

    if args.provider == "llm":
        llm_result = _try_llm_analysis(notice_text, technical_spec_text, contract_draft_text)
        if llm_result:
            analysis["llm_analysis"] = llm_result
            analysis["analysis_mode"] = "llm"
        else:
            print("  -> Falling back to stub analysis")

    print(f"  Analysis mode: {analysis.get('analysis_mode', 'stub')}")
    print(f"  Recommendation: {analysis.get('preliminary_recommendation', 'N/A')}")

    import copy
    records_with_refs = copy.deepcopy(records_info)
    for r, rec in zip(records_with_refs, intake_records):
        r["record"] = rec

    # Step 7: Build internal analysis
    print("[7] Building internal analysis report...")
    internal_md = _build_internal_analysis_markdown(
        analysis, notice_text, technical_spec_text, contract_draft_text,
        partner_profile, records_with_refs,
    )

    # Step 8: Build partner export sections
    print("[8] Building partner export sections...")
    partner_sections = _build_partner_sections(analysis)

    # Step 9: Generate export package and deliver
    print("[9] Generating export package...")
    package, delivered = _create_export_package_and_deliver(
        ws.partner_workspace_id,
        partner_sections,
        intake_records,
        tender_label,
    )

    # Step 10: Render export outputs
    print("[10] Rendering export outputs...")
    export_md = render_export_markdown(package)
    export_json = render_export_json(package)

    # Step 11: Write all output files
    print("[11] Writing output files...")
    _write_outputs(
        output_dir,
        export_dir,
        partner_id=partner_id,
        tender_dir=str(tender_dir),
        ws_id=ws.partner_workspace_id,
        records=records_info,
        analysis=analysis,
        internal_markdown=internal_md,
        package_id=package.export_package_id,
        export_md=export_md,
        export_json=export_json,
        delivery_status=delivered.export_status.value if hasattr(delivered, "export_status") else "unknown",
    )

    # Step 12: Record feedback and outcome
    print("[12] Recording feedback and outcome...")
    _record_feedback_and_outcome(
        ws.partner_workspace_id,
        package.export_package_id,
    )

    print()
    print("=== PP1 Run Complete ===")
    print(f"  Partner ID:     {partner_id}")
    print(f"  Tender dir:     {tender_dir}")
    print(f"  Output dir:     {output_dir}")
    print(f"  Export dir:     {export_dir}")


if __name__ == "__main__":
    main()
