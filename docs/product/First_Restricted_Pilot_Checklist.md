# First Restricted Pilot Checklist

Use this checklist for the first restricted paid/design-partner pilot operation.

## Phase 1: Partner Selection

- [ ] Identify a partner willing to accept manual-control restrictions.
- [ ] Confirm partner understands limitations (no automation, no EDS, manual delivery only).
- [ ] Share `Pilot_Limitations_Disclosure.md` with partner.
- [ ] Confirm partner has a real tender or data to share.
- [ ] Agree on scope, timeline, and expected outputs.

## Phase 2: Setup

- [ ] Collect company profile using `Partner_Profile_Template.md` (local only).
- [ ] Receive tender link or documents via external channel.
- [ ] Save raw documents to `local_pilot_runs/<partner_label>/raw/`.
- [ ] Create local pilot folder: `local_pilot_runs/<partner_label>/`.
- [ ] Create intake records with `create_workspace()` and `add_intake_record()`.
- [ ] Classify visibility: `classify_default_visibility()`.

## Phase 3: Redaction

- [ ] Run `require_redaction()` on each record.
- [ ] Redact sensitive data following `Redaction_Checklist.md`.
- [ ] Update redaction status per record.
- [ ] Run `generate_redaction_checklist()` to verify.

## Phase 4: System Run

- [ ] Run `check_export_readiness()` to verify workspace is ready.
- [ ] Run analysis scripts or operator console commands as needed.
- [ ] Review analysis outputs.

## Phase 5: Export Generation

- [ ] Call `generate_export_package()` with workspace ID.
- [ ] Review `included_sections`, `redacted_sections`, and `blocked_sections`.
- [ ] Resolve any blocked sections.
- [ ] Call `approve_for_delivery()`.

## Phase 6: Manual Delivery

- [ ] Render export: `render_export_markdown()` or `render_export_json()`.
- [ ] Review rendered output manually.
- [ ] Deliver to partner via external channel.
- [ ] Call `mark_delivered_manually()`.

## Phase 7: Feedback Collection

- [ ] Schedule feedback call or send `Partner_Feedback_Template.md`.
- [ ] Collect ratings, would-pay signal, and open-ended feedback.
- [ ] Record feedback with `create_feedback()`.

## Phase 8: Outcome Recording

- [ ] Review feedback and scores.
- [ ] Make next-action decision.
- [ ] Record outcome with `create_outcome()`.
- [ ] Document decision rationale.

## Phase 9: Next Step

- [ ] Execute next action per outcome.
- [ ] If GO for paid pilot: initiate paid pilot proposal.
- [ ] If ITERATE: revise workflow and repeat.
- [ ] If PAUSE/STOP: document lessons learned.

## Compliance Checks

- [ ] No real partner data was committed to the repository.
- [ ] No automated external communication was sent.
- [ ] No procurement platform interaction occurred.
- [ ] Export guard was respected throughout.
- [ ] Manual delivery checklist was followed.
- [ ] `git status` verified clean of real data before any commit.
