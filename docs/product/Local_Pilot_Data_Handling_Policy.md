# Local Pilot Data Handling Policy

## Purpose

This document defines how partner-provided data must be handled locally during restricted paid pilot operations.

## Critical Rules

1. **Real partner data must never be committed to the repository.**
2. **Real documents must stay in local ignored folders** (`local_pilot_runs/`, `pilot_runs/`, `tmp/partner_exports/`).
3. **Only redacted or synthetic outputs may be committed.**
4. **Partner-facing reports must pass the export/redaction guard before delivery.**

## Local Folder Structure

```
local_pilot_runs/
  <partner_label>/
    raw/              # Original partner documents (gitignored)
    redacted/         # Redacted versions (may be committed only if safe)
    output/           # Analysis outputs, export packages (gitignored)
    notes/            # Operator notes (gitignored, may contain sensitive info)
```

## What May Be Committed

- Redacted intake records with `redacted_for_partner_report` or `approved_for_pilot_use` status.
- Synthetic/example data in `fixtures/` directories.
- Export packages after human review with `approved_for_delivery` status.
- Feedback and outcome records (anonymized, no raw partner data).
- Templates and policies.
- Scripts and code.

## What Must NOT Be Committed

- Raw unredacted tender documents.
- Partner-identifying information in commit messages or docs.
- Credentials, API keys, or passwords.
- Real financial data, personal data, or confidential business information.
- Internal operation notes containing sensitive partner context.

## Enforcement

- `.gitignore` ignores `local_pilot_runs/`, `pilot_runs/`, and `tmp/partner_exports/`.
- Operators must run `git status` before every commit to verify no real data is staged.
- Sensitive data violations must be reported and remediated immediately.

## Export Guard Requirement

Every partner-facing report must pass through:

1. `generate_export_package()` — applies access boundary and redaction rules.
2. `can_appear_in_partner_report()` — verifies each intake record is export-safe.
3. `approve_for_delivery()` — requires explicit human approval.
4. `Manual_Delivery_Checklist.md` — final verification before manual delivery.
