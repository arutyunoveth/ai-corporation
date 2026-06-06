from src.modules.partner_export.schemas import ExportStatus
from src.modules.partner_export.service import (
    add_report_ref,
    approve_for_delivery,
    generate_export_package,
    mark_delivered_manually,
    render_export_json,
    render_export_markdown,
)
from src.modules.partner_workspace.schemas import IntakeSourceType, RedactionStatus
from src.modules.partner_workspace.service import add_intake_record
from src.modules.pilot_access_boundary.schemas import VisibilityLevel


class TestExportPackageGeneration:
    def test_export_includes_exportable_sections(self):
        sections = {"customer_report": "customer content", "summary": "summary content"}
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections=sections,
        )
        assert "customer_report" in package.included_sections
        assert "summary" in package.included_sections

    def test_export_redacts_internal_only_sections(self):
        sections = {"runtime_trace": "trace data", "internal_debug": "debug info"}
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections=sections,
        )
        assert "runtime_trace" in package.redacted_sections
        assert "internal_debug" in package.redacted_sections

    def test_export_blocks_restricted_sensitive_sections(self):
        sections = {"legal_sensitive": "legal content", "restricted_note": "restricted"}
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections=sections,
        )
        assert "legal_sensitive" in package.blocked_sections
        assert "restricted_note" in package.blocked_sections

    def test_export_omits_operator_visible(self):
        sections = {"operator_decision": "decision data", "action_log": "action"}
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections=sections,
        )
        assert "operator_decision" in package.redacted_sections
        assert "action_log" in package.redacted_sections

    def test_export_respects_intake_restricted_sensitive(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="legal note",
            source_type=IntakeSourceType.manual_notes,
            visibility_level=VisibilityLevel.restricted_sensitive,
            redaction_status=RedactionStatus.blocked_sensitive,
        )
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={},
            intake_records=[record],
        )
        assert "legal note" in package.blocked_sections

    def test_export_respects_intake_not_ready(self):
        record = add_intake_record(
            partner_workspace_id="PW-001",
            source_label="unredacted tender",
            source_type=IntakeSourceType.tender_link,
            visibility_level=VisibilityLevel.partner_visible,
            redaction_status=RedactionStatus.raw_received,
        )
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={},
            intake_records=[record],
        )
        assert "unredacted tender" in package.redacted_sections

    def test_export_blocked_status_when_blocked_sections(self):
        sections = {"restricted_note": "sensitive"}
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections=sections,
        )
        assert package.export_status == ExportStatus.blocked

    def test_export_draft_status_when_no_blocked(self):
        sections = {"customer_report": "content"}
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections=sections,
        )
        assert package.export_status == ExportStatus.draft

    def test_export_summary_includes_counts(self):
        sections = {"customer_report": "ok", "runtime_trace": "redact", "restricted_note": "block"}
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections=sections,
        )
        assert "Included (1)" in package.export_summary
        assert "Redacted (1)" in package.export_summary
        assert "Blocked (1)" in package.export_summary


class TestExportDeliveryLifecycle:
    def test_approve_for_delivery(self):
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={"report": "content"},
        )
        approved = approve_for_delivery(package)
        assert approved.export_status == ExportStatus.approved_for_delivery
        assert approved.review_status == "approved"

    def test_mark_delivered_manually(self):
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={"report": "content"},
        )
        approved = approve_for_delivery(package)
        delivered = mark_delivered_manually(approved)
        assert delivered.export_status == ExportStatus.delivered_manually
        assert delivered.review_status == "delivered"

    def test_delivered_manually_does_not_send(self):
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={"report": "content"},
        )
        delivered = mark_delivered_manually(approve_for_delivery(package))
        assert delivered.export_status == ExportStatus.delivered_manually
        assert "delivered_manually" in delivered.export_status.value
        assert not hasattr(delivered, "send_attempted")

    def test_add_report_ref(self):
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={"report": "content"},
        )
        updated = add_report_ref(package, "prebid_report", "/path/to/report.md")
        assert updated.report_refs["prebid_report"] == "/path/to/report.md"


class TestExportOutputFormat:
    def test_render_export_markdown(self):
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={"report": "content"},
        )
        md = render_export_markdown(package)
        assert "Partner Export Package" in md
        assert package.export_package_id in md
        assert package.partner_workspace_id in md

    def test_render_export_json(self):
        package = generate_export_package(
            partner_workspace_id="PW-001",
            scenario_or_tender_id="SC-001",
            report_sections={"report": "content"},
        )
        data = render_export_json(package)
        assert data["export_package_id"] == package.export_package_id
        assert data["partner_workspace_id"] == "PW-001"
        assert data["scenario_or_tender_id"] == "SC-001"


class TestDP4NoExternalAction:
    def test_export_helpers_are_pure(self):
        from src.modules.partner_export import service
        assert hasattr(service, "generate_export_package")
        assert hasattr(service, "render_export_markdown")
        assert hasattr(service, "render_export_json")
        assert hasattr(service, "approve_for_delivery")
        assert hasattr(service, "mark_delivered_manually")
        assert hasattr(service, "add_report_ref")
        assert not hasattr(service, "send_email")
        assert not hasattr(service, "upload_file")
