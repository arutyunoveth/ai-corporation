from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import Field

from src.modules.pilot_access_boundary.schemas import VisibilityLevel
from src.shared.types.common import APIModel


class PartnerStage(StrEnum):
    draft = "draft"
    active_design_partner = "active_design_partner"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class IntakeMode(StrEnum):
    synthetic = "synthetic"
    redacted_real = "redacted_real"
    manual_entry = "manual_entry"
    operator_uploaded = "operator_uploaded"
    external_reference_only = "external_reference_only"


class IntakeSourceType(StrEnum):
    tender_link = "tender_link"
    notice_text = "notice_text"
    technical_spec_text = "technical_spec_text"
    contract_draft_text = "contract_draft_text"
    quote_file_summary = "quote_file_summary"
    manual_notes = "manual_notes"
    other = "other"


class RedactionStatus(StrEnum):
    not_required = "not_required"
    raw_received = "raw_received"
    redaction_required = "redaction_required"
    pending_redaction = "pending_redaction"
    redaction_in_progress = "redaction_in_progress"
    redacted = "redacted"
    redacted_for_internal_use = "redacted_for_internal_use"
    redacted_for_partner_report = "redacted_for_partner_report"
    blocked_sensitive = "blocked_sensitive"
    needs_review = "needs_review"
    approved_for_pilot_use = "approved_for_pilot_use"


class PartnerWorkspace(APIModel):
    partner_workspace_id: str = Field(min_length=1)
    partner_label: str = Field(min_length=1)
    partner_stage: PartnerStage = PartnerStage.draft
    allowed_artifact_visibility: VisibilityLevel = VisibilityLevel.operator_visible
    intake_mode: IntakeMode = IntakeMode.manual_entry
    data_handling_notes: str = ""
    created_by: str = Field(min_length=1)
    review_status: str = "pending"
    created_at: datetime


class IntakeRecord(APIModel):
    intake_record_id: str = Field(min_length=1)
    partner_workspace_id: str = Field(min_length=1)
    source_type: IntakeSourceType = IntakeSourceType.other
    source_label: str = Field(min_length=1)
    contains_sensitive_data: bool = False
    redaction_status: RedactionStatus = RedactionStatus.not_required
    visibility_level: VisibilityLevel = VisibilityLevel.operator_visible
    operator_notes: str = ""
    linked_tender_or_scenario_id: str | None = None
    created_at: datetime
