# Manual Delivery Checklist

Use this checklist before and after delivering an export package to a design partner.

## Before Delivery

- [ ] Export package ID: _________________
- [ ] Partner workspace ID: _________________
- [ ] Export status is `approved_for_delivery`.
- [ ] All `included_sections` are reviewed and partner-safe.
- [ ] All `redacted_sections` are confirmed as safe to omit.
- [ ] All `blocked_sections` are confirmed as correctly excluded.
- [ ] No restricted_sensitive data is present in the package.
- [ ] No internal_only data is present in the package.
- [ ] No operator_visible data is present in the package.
- [ ] Export summary has been reviewed.

## Delivery

- [ ] Package is transmitted manually (email, secure portal, etc.) — outside the repository.
- [ ] After delivery, call `mark_delivered_manually()`.

## After Delivery

- [ ] Status updated to `delivered_manually`.
- [ ] Delivery recorded in partner workspace notes.
- [ ] Feedback form sent or scheduled.
- [ ] Export package archived if no longer needed.
