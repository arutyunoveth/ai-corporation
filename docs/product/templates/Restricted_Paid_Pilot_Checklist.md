# Restricted Paid Pilot Checklist

Use this checklist before, during, and after each restricted paid pilot operation.

## Pre-Pilot Setup

- [ ] Partner selected and scope confirmed.
- [ ] Company profile collected (local only, not committed).
- [ ] Tender materials received and stored in `local_pilot_runs/<partner_label>/raw/`.
- [ ] Intake records created with correct visibility and redaction status.
- [ ] Redaction checklist reviewed and applied.
- [ ] All sensitive data redacted or blocked.

## Pilot Execution

- [ ] Analysis scripts run successfully.
- [ ] Results reviewed for accuracy.
- [ ] Export package generated with `generate_export_package()`.
- [ ] Package reviewed — blocked sections resolved.
- [ ] Package approved with `approve_for_delivery()`.

## Manual Delivery

- [ ] Export package rendered to partner-ready format (markdown or JSON).
- [ ] Delivered via external channel (email, secure portal — no repository automation).
- [ ] Delivery recorded with `mark_delivered_manually()`.
- [ ] Manual Delivery Checklist completed.

## Post-Pilot

- [ ] Feedback collected (call, email, or form).
- [ ] Feedback recorded with `create_feedback()`.
- [ ] Outcome recorded with `create_outcome()`.
- [ ] Next action decided and documented.

## Compliance

- [ ] No real partner data committed to the repository.
- [ ] No automated communication sent outside the repository.
- [ ] No procurement platform interaction attempted.
- [ ] Export guard respected.
- [ ] `git status` verified before commit.

---

*This checklist is for operator use during pilot operations.*
