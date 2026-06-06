from __future__ import annotations

from datetime import UTC, datetime

from src.modules.partner_workspace.schemas import (
    IntakeMode,
    IntakeRecord,
    IntakeSourceType,
    PartnerStage,
    PartnerWorkspace,
    RedactionStatus,
)
from src.modules.pilot_access_boundary.schemas import ActorCategory, VisibilityLevel
from src.modules.pilot_access_boundary.service import (
    can_actor_view,
    can_export_to_partner,
)


def _generate_id(prefix: str) -> str:
    ts = datetime.now(UTC).strftime("%Y%m%d%H%M%S%f")
    return f"{prefix}-{ts}"


def create_workspace(
    *,
    partner_label: str,
    created_by: str,
    intake_mode: IntakeMode = IntakeMode.manual_entry,
    data_handling_notes: str = "",
) -> PartnerWorkspace:
    return PartnerWorkspace(
        partner_workspace_id=_generate_id("PW"),
        partner_label=partner_label,
        partner_stage=PartnerStage.draft,
        allowed_artifact_visibility=VisibilityLevel.operator_visible,
        intake_mode=intake_mode,
        data_handling_notes=data_handling_notes,
        created_by=created_by,
        review_status="pending",
        created_at=datetime.now(UTC),
    )


def add_intake_record(
    *,
    partner_workspace_id: str,
    source_type: IntakeSourceType = IntakeSourceType.other,
    source_label: str,
    contains_sensitive_data: bool = False,
    redaction_status: RedactionStatus = RedactionStatus.not_required,
    visibility_level: VisibilityLevel = VisibilityLevel.operator_visible,
    operator_notes: str = "",
    linked_tender_or_scenario_id: str | None = None,
) -> IntakeRecord:
    return IntakeRecord(
        intake_record_id=_generate_id("IR"),
        partner_workspace_id=partner_workspace_id,
        source_type=source_type,
        source_label=source_label,
        contains_sensitive_data=contains_sensitive_data,
        redaction_status=redaction_status,
        visibility_level=visibility_level,
        operator_notes=operator_notes,
        linked_tender_or_scenario_id=linked_tender_or_scenario_id,
        created_at=datetime.now(UTC),
    )


def classify_default_visibility(
    contains_sensitive_data: bool,
    source_type: IntakeSourceType,
    redaction_status: RedactionStatus,
) -> VisibilityLevel:
    if redaction_status == RedactionStatus.blocked_sensitive:
        return VisibilityLevel.restricted_sensitive
    if contains_sensitive_data:
        return VisibilityLevel.internal_only
    if redaction_status in (
        RedactionStatus.pending_redaction,
        RedactionStatus.needs_review,
        RedactionStatus.redaction_required,
        RedactionStatus.raw_received,
        RedactionStatus.redaction_in_progress,
    ):
        return VisibilityLevel.operator_visible
    if source_type == IntakeSourceType.manual_notes:
        return VisibilityLevel.operator_visible
    return VisibilityLevel.partner_visible


def check_export_readiness(record: IntakeRecord) -> bool:
    if record.visibility_level in (
        VisibilityLevel.internal_only,
        VisibilityLevel.restricted_sensitive,
    ):
        return False
    if record.redaction_status in (
        RedactionStatus.pending_redaction,
        RedactionStatus.blocked_sensitive,
        RedactionStatus.redaction_required,
        RedactionStatus.raw_received,
        RedactionStatus.redaction_in_progress,
    ):
        return False
    return True


def list_partner_visible_artifacts(records: list[IntakeRecord]) -> list[IntakeRecord]:
    blocked_statuses = {
        RedactionStatus.blocked_sensitive,
        RedactionStatus.pending_redaction,
        RedactionStatus.redaction_required,
        RedactionStatus.raw_received,
        RedactionStatus.redaction_in_progress,
    }
    return [
        r
        for r in records
        if can_actor_view(ActorCategory.design_partner_viewer, r.visibility_level).allowed
        and r.redaction_status not in blocked_statuses
    ]


def block_restricted_from_export(records: list[IntakeRecord]) -> list[IntakeRecord]:
    return [r for r in records if not can_export_to_partner(r.visibility_level).allowed]


def require_redaction(record: IntakeRecord) -> IntakeRecord:
    return record.model_copy(update={"redaction_status": RedactionStatus.redaction_required})


def start_redaction(record: IntakeRecord) -> IntakeRecord:
    return record.model_copy(update={"redaction_status": RedactionStatus.redaction_in_progress})


def complete_redaction(record: IntakeRecord, *, target: RedactionStatus) -> IntakeRecord:
    valid_targets = {
        RedactionStatus.redacted_for_internal_use,
        RedactionStatus.redacted_for_partner_report,
        RedactionStatus.blocked_sensitive,
    }
    if target not in valid_targets:
        raise ValueError(f"Invalid redaction target: {target.value}")
    return record.model_copy(update={"redaction_status": target})


def approve_for_pilot_use(record: IntakeRecord) -> IntakeRecord:
    return record.model_copy(update={"redaction_status": RedactionStatus.approved_for_pilot_use})


def mark_redacted_for_internal(record: IntakeRecord) -> IntakeRecord:
    return complete_redaction(record, target=RedactionStatus.redacted_for_internal_use)


def mark_redacted_for_partner(record: IntakeRecord) -> IntakeRecord:
    return complete_redaction(record, target=RedactionStatus.redacted_for_partner_report)


def block_sensitive(record: IntakeRecord) -> IntakeRecord:
    return complete_redaction(record, target=RedactionStatus.blocked_sensitive)


def can_use_in_pilot_run(record: IntakeRecord) -> bool:
    ready_statuses = {
        RedactionStatus.not_required,
        RedactionStatus.redacted,
        RedactionStatus.redacted_for_internal_use,
        RedactionStatus.redacted_for_partner_report,
        RedactionStatus.approved_for_pilot_use,
    }
    return record.redaction_status in ready_statuses


def can_appear_in_partner_report(record: IntakeRecord) -> bool:
    if record.visibility_level not in (
        VisibilityLevel.partner_visible,
        VisibilityLevel.exportable_to_partner,
    ):
        return False
    allowed_statuses = {
        RedactionStatus.not_required,
        RedactionStatus.redacted,
        RedactionStatus.redacted_for_partner_report,
        RedactionStatus.approved_for_pilot_use,
    }
    return record.redaction_status in allowed_statuses


def generate_redaction_checklist(records: list[IntakeRecord]) -> list[dict]:
    checklist = []
    for record in records:
        entry = {
            "intake_record_id": record.intake_record_id,
            "source_label": record.source_label,
            "source_type": record.source_type.value,
            "contains_sensitive_data": record.contains_sensitive_data,
            "redaction_status": record.redaction_status.value,
            "visibility_level": record.visibility_level.value,
            "needs_redaction": record.redaction_status
            in (RedactionStatus.raw_received, RedactionStatus.redaction_required),
            "can_use_in_pilot": can_use_in_pilot_run(record),
            "can_appear_in_partner_report": can_appear_in_partner_report(record),
        }
        checklist.append(entry)
    return checklist
