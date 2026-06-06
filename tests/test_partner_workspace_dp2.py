from src.modules.partner_workspace.schemas import (
    IntakeMode,
    IntakeSourceType,
    PartnerStage,
    RedactionStatus,
)
from src.modules.partner_workspace.service import (
    add_intake_record,
    block_restricted_from_export,
    check_export_readiness,
    classify_default_visibility,
    create_workspace,
    list_partner_visible_artifacts,
)
from src.modules.pilot_access_boundary.schemas import ActorCategory, VisibilityLevel
from src.modules.pilot_access_boundary.service import can_actor_view


class TestPartnerWorkspace:
    def test_create_workspace(self):
        ws = create_workspace(partner_label="Test Partner A", created_by="operator-1")
        assert ws.partner_workspace_id.startswith("PW-")
        assert ws.partner_label == "Test Partner A"
        assert ws.partner_stage == PartnerStage.draft
        assert ws.created_by == "operator-1"

    def test_create_workspace_custom_intake_mode(self):
        ws = create_workspace(
            partner_label="Test Partner B",
            created_by="operator-2",
            intake_mode=IntakeMode.synthetic,
            data_handling_notes="synthetic data only",
        )
        assert ws.intake_mode == IntakeMode.synthetic
        assert ws.data_handling_notes == "synthetic data only"

    def test_workspace_default_visibility(self):
        ws = create_workspace(partner_label="Test", created_by="op")
        assert ws.allowed_artifact_visibility == VisibilityLevel.operator_visible


class TestIntakeRecord:
    def test_create_intake_record(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_type=IntakeSourceType.notice_text,
            source_label="Notice of tender #123",
        )
        assert record.intake_record_id.startswith("IR-")
        assert record.partner_workspace_id == "PW-001"
        assert record.source_type == IntakeSourceType.notice_text
        assert record.source_label == "Notice of tender #123"

    def test_intake_record_sensitive_data(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_type=IntakeSourceType.contract_draft_text,
            source_label="Contract draft",
            contains_sensitive_data=True,
            visibility_level=VisibilityLevel.internal_only,
        )
        assert record.contains_sensitive_data
        assert record.visibility_level == VisibilityLevel.internal_only


class TestDefaultVisibility:
    def test_blocked_sensitive_returns_restricted(self):
        v = classify_default_visibility(
            contains_sensitive_data=False,
            source_type=IntakeSourceType.tender_link,
            redaction_status=RedactionStatus.blocked_sensitive,
        )
        assert v == VisibilityLevel.restricted_sensitive

    def test_sensitive_data_returns_internal_only(self):
        v = classify_default_visibility(
            contains_sensitive_data=True,
            source_type=IntakeSourceType.tender_link,
            redaction_status=RedactionStatus.not_required,
        )
        assert v == VisibilityLevel.internal_only

    def test_pending_redaction_returns_operator_visible(self):
        v = classify_default_visibility(
            contains_sensitive_data=False,
            source_type=IntakeSourceType.tender_link,
            redaction_status=RedactionStatus.pending_redaction,
        )
        assert v == VisibilityLevel.operator_visible

    def test_needs_review_returns_operator_visible(self):
        v = classify_default_visibility(
            contains_sensitive_data=False,
            source_type=IntakeSourceType.tender_link,
            redaction_status=RedactionStatus.needs_review,
        )
        assert v == VisibilityLevel.operator_visible

    def test_manual_notes_returns_operator_visible(self):
        v = classify_default_visibility(
            contains_sensitive_data=False,
            source_type=IntakeSourceType.manual_notes,
            redaction_status=RedactionStatus.not_required,
        )
        assert v == VisibilityLevel.operator_visible

    def test_clean_intake_returns_partner_visible(self):
        v = classify_default_visibility(
            contains_sensitive_data=False,
            source_type=IntakeSourceType.notice_text,
            redaction_status=RedactionStatus.not_required,
        )
        assert v == VisibilityLevel.partner_visible


class TestExportReadiness:
    def test_internal_only_not_exportable(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="internal trace",
            visibility_level=VisibilityLevel.internal_only,
        )
        assert not check_export_readiness(record)

    def test_restricted_sensitive_not_exportable(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="sensitive note",
            visibility_level=VisibilityLevel.restricted_sensitive,
        )
        assert not check_export_readiness(record)

    def test_pending_redaction_not_exportable(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="needs redaction",
            redaction_status=RedactionStatus.pending_redaction,
            visibility_level=VisibilityLevel.operator_visible,
        )
        assert not check_export_readiness(record)

    def test_blocked_sensitive_not_exportable(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="blocked",
            redaction_status=RedactionStatus.blocked_sensitive,
        )
        assert not check_export_readiness(record)

    def test_clean_partner_visible_exportable(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="clean report",
            visibility_level=VisibilityLevel.partner_visible,
            redaction_status=RedactionStatus.redacted,
        )
        assert check_export_readiness(record)


class TestPartnerVisibleListing:
    def test_partner_visible_list_excludes_internal(self):
        records = [
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="internal trace",
                visibility_level=VisibilityLevel.internal_only,
            ),
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="partner report",
                visibility_level=VisibilityLevel.partner_visible,
                redaction_status=RedactionStatus.redacted,
            ),
        ]
        visible = list_partner_visible_artifacts(records)
        assert len(visible) == 1
        assert visible[0].source_label == "partner report"

    def test_partner_visible_list_excludes_blocked_sensitive(self):
        records = [
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="blocked",
                visibility_level=VisibilityLevel.restricted_sensitive,
                redaction_status=RedactionStatus.blocked_sensitive,
            ),
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="clean",
                visibility_level=VisibilityLevel.partner_visible,
                redaction_status=RedactionStatus.not_required,
            ),
        ]
        visible = list_partner_visible_artifacts(records)
        assert len(visible) == 1
        assert visible[0].source_label == "clean"

    def test_partner_visible_list_excludes_operator_visible(self):
        records = [
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="operator decision",
                visibility_level=VisibilityLevel.operator_visible,
            ),
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="exportable report",
                visibility_level=VisibilityLevel.exportable_to_partner,
                redaction_status=RedactionStatus.redacted,
            ),
        ]
        visible = list_partner_visible_artifacts(records)
        assert len(visible) == 1
        assert visible[0].source_label == "exportable report"


class TestBlockRestricted:
    def test_block_restricted_identifies_non_exportable(self):
        records = [
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="internal",
                visibility_level=VisibilityLevel.internal_only,
            ),
            add_intake_record(
                partner_workspace_id="PW-001",
                source_label="exportable",
                visibility_level=VisibilityLevel.partner_visible,
                redaction_status=RedactionStatus.redacted,
            ),
        ]
        blocked = block_restricted_from_export(records)
        assert len(blocked) == 1
        assert blocked[0].source_label == "internal"


class TestDP2AccessBoundaryRespected:
    def test_design_partner_cannot_view_internal_intake(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="internal",
            visibility_level=VisibilityLevel.internal_only,
        )
        result = can_actor_view(ActorCategory.design_partner_viewer, record.visibility_level)
        assert not result.allowed

    def test_design_partner_cannot_view_restricted_intake(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="restricted",
            visibility_level=VisibilityLevel.restricted_sensitive,
        )
        result = can_actor_view(ActorCategory.design_partner_viewer, record.visibility_level)
        assert not result.allowed

    def test_design_partner_can_view_partner_visible_intake(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="visible",
            visibility_level=VisibilityLevel.partner_visible,
        )
        result = can_actor_view(ActorCategory.design_partner_viewer, record.visibility_level)
        assert result.allowed


class TestDP2NoExternalAction:
    def test_no_endpoints_created(self):
        from src.modules.partner_workspace import service, schemas
        assert hasattr(service, "create_workspace")
        assert hasattr(service, "add_intake_record")
        assert hasattr(service, "classify_default_visibility")
        assert hasattr(service, "check_export_readiness")
        assert hasattr(service, "list_partner_visible_artifacts")
        assert hasattr(service, "block_restricted_from_export")
        assert hasattr(schemas, "PartnerWorkspace")
        assert hasattr(schemas, "IntakeRecord")
        assert hasattr(schemas, "PartnerStage")
        assert hasattr(schemas, "IntakeMode")
        assert hasattr(schemas, "IntakeSourceType")
        assert hasattr(schemas, "RedactionStatus")
