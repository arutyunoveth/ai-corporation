# Redaction Checklist

Use this checklist before any design-partner pilot run to ensure all tender materials are properly handled.

## Per Intake Record

- [ ] Record ID: _________________
- [ ] Source label: _________________
- [ ] Source type: _________________
- [ ] Contains sensitive data? [ ] Yes [ ] No
- [ ] Redaction status: _________________

### If `raw_received`:
- [ ] Assess whether redaction is needed.
- [ ] If needed, update status to `redaction_required`.
- [ ] If not needed, update status to `not_required`.

### If `redaction_required` or `redaction_in_progress`:
- [ ] Complete redaction.
- [ ] Update status to `redacted_for_internal_use` or `redacted_for_partner_report`.
- [ ] If too sensitive, update status to `blocked_sensitive`.

### If `redacted_for_internal_use`:
- [ ] Determine if also safe for partner.
- [ ] If yes, update to `redacted_for_partner_report`.
- [ ] If no, keep as `redacted_for_internal_use`.

### If `redacted_for_partner_report` or `approved_for_pilot_use`:
- [ ] Verify visibility level allows export (must be `partner_visible` or `exportable_to_partner`).
- [ ] Record is ready for pilot runs and partner reports (if visibility allows).

### If `blocked_sensitive`:
- [ ] Record must not appear in any pilot run or export.
- [ ] Mark as `restricted_sensitive` visibility.

## Final Verification

- [ ] Run `generate_redaction_checklist()` for all records.
- [ ] Verify `can_use_in_pilot_run()` for each record used in the pilot.
- [ ] Verify `can_appear_in_partner_report()` for each record in the export.
- [ ] No real sensitive data committed to repository.
- [ ] All automated runs use synthetic or redacted-real fixtures only.
