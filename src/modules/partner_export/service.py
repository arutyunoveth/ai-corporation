from __future__ import annotations

from datetime import UTC, datetime

from src.modules.partner_export.schemas import ExportPackage, ExportStatus
from src.modules.partner_workspace.schemas import IntakeRecord, RedactionStatus
from src.modules.partner_workspace.service import can_appear_in_partner_report
from src.modules.pilot_access_boundary.schemas import VisibilityLevel
from src.modules.pilot_access_boundary.service import can_export_to_partner


def _generate_id(prefix: str) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{ts}"


def generate_export_package(
    *,
    partner_workspace_id: str,
    scenario_or_tender_id: str,
    report_sections: dict[str, str],
    intake_records: list[IntakeRecord] | None = None,
) -> ExportPackage:
    included: list[str] = []
    redacted: list[str] = []
    blocked: list[str] = []

    for label, _content in report_sections.items():
        visibility = _infer_section_visibility(label)
        export_check = can_export_to_partner(visibility)
        if export_check.allowed:
            included.append(label)
        elif visibility == VisibilityLevel.restricted_sensitive:
            blocked.append(label)
        else:
            redacted.append(label)

    if intake_records:
        for record in intake_records:
            if record.visibility_level == VisibilityLevel.restricted_sensitive:
                if record.source_label not in blocked:
                    blocked.append(record.source_label)
            elif not can_appear_in_partner_report(record):
                redacted.append(record.source_label)
            else:
                if record.source_label not in included:
                    included.append(record.source_label)

    export_status = ExportStatus.blocked if blocked else ExportStatus.draft

    summary_parts = []
    if included:
        summary_parts.append(f"Included ({len(included)}): {', '.join(included)}")
    if redacted:
        summary_parts.append(f"Redacted ({len(redacted)}): {', '.join(redacted)}")
    if blocked:
        summary_parts.append(f"Blocked ({len(blocked)}): {', '.join(blocked)}")
    export_summary = "; ".join(summary_parts) if summary_parts else "No sections processed"

    return ExportPackage(
        export_package_id=_generate_id("EP"),
        partner_workspace_id=partner_workspace_id,
        scenario_or_tender_id=scenario_or_tender_id,
        report_refs={},
        included_sections=included,
        redacted_sections=redacted,
        blocked_sections=blocked,
        export_status=export_status,
        review_status="pending",
        export_summary=export_summary,
        created_at=datetime.now(UTC),
    )


def _infer_section_visibility(section_label: str) -> VisibilityLevel:
    label_lower = section_label.lower()
    if any(word in label_lower for word in ("trace", "internal", "debug")):
        return VisibilityLevel.internal_only
    if any(word in label_lower for word in ("sensitive", "legal", "restricted")):
        return VisibilityLevel.restricted_sensitive
    if any(word in label_lower for word in ("operator", "decision", "action")):
        return VisibilityLevel.operator_visible
    if any(word in label_lower for word in ("customer", "report", "summary")):
        return VisibilityLevel.exportable_to_partner
    return VisibilityLevel.partner_visible


def render_export_markdown(package: ExportPackage) -> str:
    lines = [
        "# Partner Export Package",
        "",
        f"- Export package ID: {package.export_package_id}",
        f"- Partner workspace ID: {package.partner_workspace_id}",
        f"- Scenario / tender ID: {package.scenario_or_tender_id}",
        f"- Export status: {package.export_status.value}",
        f"- Review status: {package.review_status}",
        f"- Created at (UTC): {package.created_at.isoformat()}",
        "",
        "## Export Summary",
        f"",
        package.export_summary,
        "",
        "## Included Sections",
    ]
    for section in package.included_sections:
        lines.append(f"- {section}")
    lines.append("")
    lines.append("## Redacted Sections")
    for section in package.redacted_sections:
        lines.append(f"- {section}")
    lines.append("")
    lines.append("## Blocked Sections")
    for section in package.blocked_sections:
        lines.append(f"- {section}")
    lines.append("")
    lines.append("## Export Rules Applied")
    lines.append("- Internal-only sections: redacted")
    lines.append("- Restricted-sensitive sections: blocked")
    lines.append("- Operator-visible sections: omitted from partner package")
    lines.append("- Human review required before delivery")
    lines.append("- This package was generated for manual delivery only")
    return "\n".join(lines)


def render_export_json(package: ExportPackage) -> dict:
    return {
        "export_package_id": package.export_package_id,
        "partner_workspace_id": package.partner_workspace_id,
        "scenario_or_tender_id": package.scenario_or_tender_id,
        "export_status": package.export_status.value,
        "review_status": package.review_status,
        "included_sections": package.included_sections,
        "redacted_sections": package.redacted_sections,
        "blocked_sections": package.blocked_sections,
        "export_summary": package.export_summary,
        "created_at": package.created_at.isoformat(),
    }


def approve_for_delivery(package: ExportPackage) -> ExportPackage:
    return package.model_copy(update={"export_status": ExportStatus.approved_for_delivery, "review_status": "approved"})


def mark_delivered_manually(package: ExportPackage) -> ExportPackage:
    return package.model_copy(update={"export_status": ExportStatus.delivered_manually, "review_status": "delivered"})


def add_report_ref(package: ExportPackage, label: str, ref: str) -> ExportPackage:
    new_refs = dict(package.report_refs)
    new_refs[label] = ref
    return package.model_copy(update={"report_refs": new_refs})
