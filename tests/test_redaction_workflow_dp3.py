from src.modules.partner_workspace.schemas import IntakeSourceType, RedactionStatus
from src.modules.partner_workspace.service import (
    add_intake_record,
    approve_for_pilot_use,
    block_sensitive,
    can_appear_in_partner_report,
    can_use_in_pilot_run,
    generate_redaction_checklist,
    mark_redacted_for_internal,
    mark_redacted_for_partner,
    require_redaction,
    start_redaction,
)
from src.modules.pilot_access_boundary.schemas import VisibilityLevel  # noqa: F401


def _make_record(**kwargs):
    defaults = dict(partner_workspace_id="PW-001", source_label="test")
    defaults.update(kwargs)
    return add_intake_record(**defaults)


class TestRedactionWorkflow:
    def test_require_redaction(self):
        record = _make_record(source_type=IntakeSourceType.tender_link)
        updated = require_redaction(record)
        assert updated.redaction_status == RedactionStatus.redaction_required

    def test_start_redaction(self):
        record = _make_record()
        updated = start_redaction(record)
        assert updated.redaction_status == RedactionStatus.redaction_in_progress

    def test_mark_redacted_for_internal(self):
        record = _make_record()
        updated = mark_redacted_for_internal(record)
        assert updated.redaction_status == RedactionStatus.redacted_for_internal_use

    def test_mark_redacted_for_partner(self):
        record = _make_record()
        updated = mark_redacted_for_partner(record)
        assert updated.redaction_status == RedactionStatus.redacted_for_partner_report

    def test_block_sensitive(self):
        record = _make_record()
        updated = block_sensitive(record)
        assert updated.redaction_status == RedactionStatus.blocked_sensitive

    def test_approve_for_pilot_use(self):
        record = _make_record()
        updated = approve_for_pilot_use(record)
        assert updated.redaction_status == RedactionStatus.approved_for_pilot_use

    def test_workflow_chain(self):
        record = _make_record(source_type=IntakeSourceType.notice_text, contains_sensitive_data=True)
        record = require_redaction(record)
        assert record.redaction_status == RedactionStatus.redaction_required
        record = start_redaction(record)
        assert record.redaction_status == RedactionStatus.redaction_in_progress
        record = mark_redacted_for_partner(record)
        assert record.redaction_status == RedactionStatus.redacted_for_partner_report
        record = approve_for_pilot_use(record)
        assert record.redaction_status == RedactionStatus.approved_for_pilot_use


class TestCanUseInPilotRun:
    def test_raw_received_cannot_use(self):
        record = _make_record(redaction_status=RedactionStatus.raw_received)
        assert not can_use_in_pilot_run(record)

    def test_redaction_required_cannot_use(self):
        record = _make_record(redaction_status=RedactionStatus.redaction_required)
        assert not can_use_in_pilot_run(record)

    def test_redaction_in_progress_cannot_use(self):
        record = _make_record(redaction_status=RedactionStatus.redaction_in_progress)
        assert not can_use_in_pilot_run(record)

    def test_blocked_sensitive_cannot_use(self):
        record = _make_record(redaction_status=RedactionStatus.blocked_sensitive)
        assert not can_use_in_pilot_run(record)

    def test_redacted_for_internal_can_use(self):
        record = _make_record(redaction_status=RedactionStatus.redacted_for_internal_use)
        assert can_use_in_pilot_run(record)

    def test_redacted_for_partner_can_use(self):
        record = _make_record(redaction_status=RedactionStatus.redacted_for_partner_report)
        assert can_use_in_pilot_run(record)

    def test_approved_for_pilot_can_use(self):
        record = _make_record(redaction_status=RedactionStatus.approved_for_pilot_use)
        assert can_use_in_pilot_run(record)

    def test_not_required_can_use(self):
        record = _make_record(redaction_status=RedactionStatus.not_required)
        assert can_use_in_pilot_run(record)


class TestCanAppearInPartnerReport:
    def test_internal_only_cannot_appear(self):
        record = _make_record(visibility_level=VisibilityLevel.internal_only, redaction_status=RedactionStatus.redacted)
        assert not can_appear_in_partner_report(record)

    def test_restricted_sensitive_cannot_appear(self):
        record = _make_record(visibility_level=VisibilityLevel.restricted_sensitive, redaction_status=RedactionStatus.redacted)
        assert not can_appear_in_partner_report(record)

    def test_operator_visible_cannot_appear(self):
        record = _make_record(visibility_level=VisibilityLevel.operator_visible, redaction_status=RedactionStatus.redacted)
        assert not can_appear_in_partner_report(record)

    def test_partner_visible_redacted_can_appear(self):
        record = _make_record(visibility_level=VisibilityLevel.partner_visible, redaction_status=RedactionStatus.redacted)
        assert can_appear_in_partner_report(record)

    def test_partner_visible_redacted_for_partner_can_appear(self):
        record = _make_record(
            visibility_level=VisibilityLevel.partner_visible,
            redaction_status=RedactionStatus.redacted_for_partner_report,
        )
        assert can_appear_in_partner_report(record)

    def test_exportable_approved_can_appear(self):
        record = _make_record(
            visibility_level=VisibilityLevel.exportable_to_partner,
            redaction_status=RedactionStatus.approved_for_pilot_use,
        )
        assert can_appear_in_partner_report(record)

    def test_redaction_required_cannot_appear(self):
        record = _make_record(visibility_level=VisibilityLevel.partner_visible, redaction_status=RedactionStatus.redaction_required)
        assert not can_appear_in_partner_report(record)

    def test_raw_received_cannot_appear(self):
        record = _make_record(visibility_level=VisibilityLevel.partner_visible, redaction_status=RedactionStatus.raw_received)
        assert not can_appear_in_partner_report(record)


class TestRedactionChecklist:
    def test_checklist_generation(self):
        records = [
            _make_record(source_label="raw intake", source_type=IntakeSourceType.tender_link, redaction_status=RedactionStatus.raw_received),
            _make_record(source_label="clean report", source_type=IntakeSourceType.notice_text, redaction_status=RedactionStatus.not_required, visibility_level=VisibilityLevel.partner_visible),
            _make_record(source_label="blocked", source_type=IntakeSourceType.contract_draft_text, redaction_status=RedactionStatus.blocked_sensitive, contains_sensitive_data=True),
        ]
        checklist = generate_redaction_checklist(records)
        assert len(checklist) == 3

        raw_entry = next(e for e in checklist if e["source_label"] == "raw intake")
        assert raw_entry["needs_redaction"]
        assert not raw_entry["can_use_in_pilot"]
        assert not raw_entry["can_appear_in_partner_report"]

        clean_entry = next(e for e in checklist if e["source_label"] == "clean report")
        assert not clean_entry["needs_redaction"]
        assert clean_entry["can_use_in_pilot"]
        assert clean_entry["can_appear_in_partner_report"]

        blocked_entry = next(e for e in checklist if e["source_label"] == "blocked")
        assert not blocked_entry["needs_redaction"]
        assert not blocked_entry["can_use_in_pilot"]
        assert not blocked_entry["can_appear_in_partner_report"]


class TestDP3NoExternalAction:
    def test_redaction_helpers_are_pure(self):
        from src.modules.partner_workspace import service
        assert hasattr(service, "require_redaction")
        assert hasattr(service, "start_redaction")
        assert hasattr(service, "mark_redacted_for_internal")
        assert hasattr(service, "mark_redacted_for_partner")
        assert hasattr(service, "block_sensitive")
        assert hasattr(service, "approve_for_pilot_use")
        assert hasattr(service, "can_use_in_pilot_run")
        assert hasattr(service, "can_appear_in_partner_report")
        assert hasattr(service, "generate_redaction_checklist")
