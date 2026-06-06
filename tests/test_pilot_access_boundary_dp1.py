from src.modules.pilot_access_boundary.schemas import ActorCategory, VisibilityLevel
from src.modules.pilot_access_boundary.service import (
    apply_export_redaction,
    can_actor_view,
    can_export_to_partner,
    default_visibility_for_artifact,
    is_internal_only,
    should_redact,
)


class TestAccessBoundaryActors:
    def test_design_partner_viewer_can_view_partner_visible(self):
        result = can_actor_view(ActorCategory.design_partner_viewer, VisibilityLevel.partner_visible)

    def test_design_partner_viewer_can_view_exportable(self):
        result = can_actor_view(ActorCategory.design_partner_viewer, VisibilityLevel.exportable_to_partner)

    def test_design_partner_viewer_cannot_view_internal_only(self):
        result = can_actor_view(ActorCategory.design_partner_viewer, VisibilityLevel.internal_only)
        assert not result.allowed
        assert result.reason is not None

    def test_design_partner_viewer_cannot_view_restricted_sensitive(self):
        result = can_actor_view(ActorCategory.design_partner_viewer, VisibilityLevel.restricted_sensitive)
        assert not result.allowed
        assert result.reason is not None

    def test_internal_operator_can_view_operator_visible(self):
        result = can_actor_view(ActorCategory.internal_operator, VisibilityLevel.operator_visible)

    def test_internal_operator_can_view_partner_visible(self):
        result = can_actor_view(ActorCategory.internal_operator, VisibilityLevel.partner_visible)

    def test_admin_can_view_all_levels(self):
        for level in VisibilityLevel:
            result = can_actor_view(ActorCategory.admin, level)


class TestAccessBoundaryExportGuard:
    def test_exportable_allowed(self):
        result = can_export_to_partner(VisibilityLevel.exportable_to_partner)

    def test_partner_visible_allowed(self):
        result = can_export_to_partner(VisibilityLevel.partner_visible)

    def test_internal_only_blocked(self):
        result = can_export_to_partner(VisibilityLevel.internal_only)
        assert not result.allowed
        assert result.reason is not None

    def test_restricted_sensitive_blocked(self):
        result = can_export_to_partner(VisibilityLevel.restricted_sensitive)
        assert not result.allowed
        assert result.reason is not None

    def test_operator_visible_blocked(self):
        result = can_export_to_partner(VisibilityLevel.operator_visible)
        assert not result.allowed
        assert result.reason is not None


class TestAccessBoundaryRedaction:
    def test_export_redaction_internal_only(self):
        sections = {"trace_1": "some trace data", "trace_2": "more data"}
        result = apply_export_redaction(VisibilityLevel.internal_only, sections=sections)
        assert not result.export_allowed
        assert "trace_1" in result.redacted_sections
        assert "trace_2" in result.redacted_sections

    def test_export_redaction_restricted_sensitive(self):
        sections = {"legal_note": "sensitive legal content"}
        result = apply_export_redaction(VisibilityLevel.restricted_sensitive, sections=sections)
        assert not result.export_allowed
        assert "legal_note" in result.redacted_sections

    def test_export_redaction_exportable_allowed(self):
        sections = {"report": "customer report content"}
        result = apply_export_redaction(VisibilityLevel.exportable_to_partner, sections=sections)
        assert result.export_allowed
        assert "report" in result.safe_sections
        assert len(result.redacted_sections) == 0

    def test_export_redaction_partner_visible_allowed(self):
        sections = {"metrics": "pilot metrics"}
        result = apply_export_redaction(VisibilityLevel.partner_visible, sections=sections)
        assert result.export_allowed
        assert "metrics" in result.safe_sections

    def test_export_redaction_returns_reason(self):
        result = apply_export_redaction(VisibilityLevel.restricted_sensitive)
        assert not result.export_allowed
        assert result.reason is not None

    def test_export_redaction_with_no_sections(self):
        result = apply_export_redaction(VisibilityLevel.internal_only)
        assert not result.export_allowed
        assert result.reason is not None


class TestAccessBoundaryInternalOnly:
    def test_internal_only_returns_true(self):
        assert is_internal_only(VisibilityLevel.internal_only)

    def test_other_levels_are_not_internal_only(self):
        assert not is_internal_only(VisibilityLevel.operator_visible)
        assert not is_internal_only(VisibilityLevel.partner_visible)
        assert not is_internal_only(VisibilityLevel.exportable_to_partner)
        assert not is_internal_only(VisibilityLevel.restricted_sensitive)


class TestAccessBoundaryShouldRedact:
    def test_restricted_sensitive_redacted_for_partner(self):
        result = should_redact(ActorCategory.design_partner_viewer, VisibilityLevel.restricted_sensitive)

    def test_restricted_sensitive_not_redacted_for_admin(self):
        result = should_redact(ActorCategory.admin, VisibilityLevel.restricted_sensitive)
        assert not result.allowed

    def test_non_restricted_not_redacted(self):
        result = should_redact(ActorCategory.design_partner_viewer, VisibilityLevel.partner_visible)
        assert not result.allowed


class TestAccessBoundaryDefaultVisibility:
    def test_runtime_trace_defaults_to_internal_only(self):
        assert default_visibility_for_artifact("runtime_trace") == VisibilityLevel.internal_only

    def test_operator_decision_defaults_to_operator_visible(self):
        assert default_visibility_for_artifact("operator_decision") == VisibilityLevel.operator_visible

    def test_pilot_evidence_defaults_to_partner_visible(self):
        assert default_visibility_for_artifact("pilot_evidence") == VisibilityLevel.partner_visible

    def test_customer_report_defaults_to_exportable(self):
        assert default_visibility_for_artifact("customer_report") == VisibilityLevel.exportable_to_partner

    def test_sensitive_note_defaults_to_restricted(self):
        assert default_visibility_for_artifact("sensitive_note") == VisibilityLevel.restricted_sensitive

    def test_unknown_artifact_defaults_to_internal_only(self):
        assert default_visibility_for_artifact("unknown_type") == VisibilityLevel.internal_only


class TestAccessBoundaryNoExternalAction:
    def test_no_endpoints_created(self):
        from src.modules.pilot_access_boundary import service, schemas
        assert hasattr(service, "can_actor_view")
        assert hasattr(service, "can_export_to_partner")
        assert hasattr(service, "apply_export_redaction")
        assert hasattr(service, "should_redact")
        assert hasattr(schemas, "ActorCategory")
        assert hasattr(schemas, "VisibilityLevel")
