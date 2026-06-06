# Real Tender Data Handling Policy

## Purpose

This document defines how real or redacted tender materials may be handled during design-partner pilots.

## Critical Rules

1. **Never commit real customer/partner data to this repository.**
2. Always use `synthetic` or `redacted_real` intake modes for any material used in automated runs.
3. Always mark records containing personal, financial, or confidential information as `contains_sensitive_data`.
4. Redact all sensitive information before using materials in any automated or partner-facing flow.
5. Blocked-sensitive records must never appear in any pilot run or export.

## Redaction Workflow

The redaction workflow moves materials through these stages:

```
raw_received
  → redaction_required
    → redaction_in_progress
      → redacted_for_internal_use
        → redacted_for_partner_report (if operator approves)
      → blocked_sensitive (if too sensitive to use)
      → approved_for_pilot_use (directly if already suitable)
```

## Redaction Status Meanings

| Status | Meaning | Can use in pilot? | Can export? |
|--------|---------|-------------------|-------------|
| `raw_received` | Material just arrived | No | No |
| `redaction_required` | Operator marked for redaction | No | No |
| `redaction_in_progress` | Redaction in progress | No | No |
| `redacted_for_internal_use` | Redacted for internal use only | Yes | No |
| `redacted_for_partner_report` | Redacted and partner-safe | Yes | Yes (if visibility allows) |
| `blocked_sensitive` | Too sensitive to use | No | No |
| `approved_for_pilot_use` | Cleared for pilot runs | Yes | Yes (if visibility allows) |
| `not_required` | No redaction needed | Yes | Yes (if visibility allows) |
| `redacted` | Redaction complete (legacy) | Yes | Yes (if visibility allows) |

## Visibility Rules

Records in raw/required/in-progress states default to `operator_visible`.
Records with sensitive content default to `internal_only`.
Blocked-sensitive records default to `restricted_sensitive`.
Only partner-safe, redacted, or approved records can reach `partner_visible` or `exportable_to_partner`.

## Operator Checklist

Before using any tender material in a pilot run:

1. Is this real customer data? → Do not commit. Use redacted or synthetic fixtures.
2. Does the record contain sensitive data? → Mark `contains_sensitive_data`.
3. Has the material been redacted? → If no, mark `redaction_required`.
4. Is the redaction complete and partner-safe? → Mark `redacted_for_partner_report`.
5. Is the material too sensitive to use at all? → Mark `blocked_sensitive`.
6. Run `generate_redaction_checklist()` to verify all records before a pilot run.

## Enforcement

- `can_use_in_pilot_run()` — gates whether a record can be used in automated runs.
- `can_appear_in_partner_report()` — gates whether a record can be exported.
- `check_export_readiness()` — combined visibility + redaction gate.
- `generate_redaction_checklist()` — produces a full audit of all records.
