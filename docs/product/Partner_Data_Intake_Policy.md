# Partner Data Intake Policy

## Purpose

This document defines how partner-provided tender materials are handled, classified, and protected within the design-partner pilot workspace.

## Important Disclaimers

- **This is a pilot data intake policy, not a production data-security framework.**
- **Real customer/partner data must never be committed to the repository.**
- **Sensitive data must be redacted before any pilot-facing use.**
- **This policy does not replace proper enterprise data governance.**

## Partner Workspace

Every design partner engagement is represented by a workspace record with:

- `partner_label`: anonymized partner name or identifier
- `partner_stage`: draft, active, paused, completed, or archived
- `allowed_artifact_visibility`: default visibility level for workspace artifacts
- `intake_mode`: how materials were obtained
- `data_handling_notes`: operator notes about data treatment
- `review_status`: pending or reviewed

## Intake Records

Every source document or material provided by a partner is represented by an intake record:

- `source_type`: type of source material
- `source_label`: human-readable label
- `contains_sensitive_data`: flag for sensitive content
- `redaction_status`: not_required, pending_redaction, redacted, blocked_sensitive, needs_review
- `visibility_level`: access boundary level (default `operator_visible`)

## Default Visibility Classification

| Condition | Default Visibility |
|-----------|-------------------|
| `blocked_sensitive` redaction | `restricted_sensitive` |
| `contains_sensitive_data == true` | `internal_only` |
| `pending_redaction` or `needs_review` | `operator_visible` |
| `manual_notes` source | `operator_visible` |
| Other cases | `partner_visible` |

## Export Rules

1. `restricted_sensitive` intake records are always blocked from partner export.
2. `internal_only` intake records cannot be exported.
3. Records with `pending_redaction` or `blocked_sensitive` redaction status cannot be exported.
4. Only `partner_visible` or `exportable_to_partner` records with `not_required` or `redacted` status may be exported.

## Operator Responsibilities

1. Mark records as `contains_sensitive_data` if they contain personal, financial, or confidential information.
2. Ensure sensitive records are redacted before any partner-facing use.
3. Never commit real customer/partner data to the repository.
4. Use `synthetic` or `redacted_real` intake modes for any material used in automated runs.
5. Record data handling notes in the workspace for audit traceability.

## Redaction Workflow

See `Real_Tender_Data_Handling_Policy.md` and `Redaction_Checklist.md` for the full redaction workflow and checklist.

Key redaction helpers:
- `require_redaction()` — mark a record as needing redaction
- `start_redaction()` — mark redaction in progress
- `mark_redacted_for_internal()` — redacted for internal use only
- `mark_redacted_for_partner()` — redacted and partner-safe
- `block_sensitive()` — too sensitive, blocked permanently
- `approve_for_pilot_use()` — cleared for pilot runs
- `can_use_in_pilot_run()` — checks if a record is safe to use in automated runs
- `can_appear_in_partner_report()` — checks if a record can be exported
- `generate_redaction_checklist()` — produces a full audit for all records

## Enforced Via

- `classify_default_visibility()` — automatic visibility assignment on intake
- `check_export_readiness()` — gate for partner-facing use
- `list_partner_visible_artifacts()` — safe listing restricted by actor category
- `block_restricted_from_export()` — identifies records blocked from export
- `can_use_in_pilot_run()` — gates pilot run participation
- `can_appear_in_partner_report()` — gates partner report inclusion
