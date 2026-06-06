# Partner Report Export Policy

## Purpose

This document defines how partner-facing report exports are generated, reviewed, and delivered during design-partner pilots.

## Important Disclaimers

- **This is a manual delivery process, not an automated external delivery system.**
- **The repository never sends emails, uploads files, or contacts partners.**
- **All exports are delivered manually by a human operator.**

## Export Process

1. Operator requests export package generation.
2. Export generator collects customer-facing report sections.
3. DP1 access boundary is applied: internal/restricted/operator sections are filtered.
4. DP3 redaction rules are applied: raw/unredacted records are excluded.
5. Package is created as `draft` or `blocked`.
6. Operator reviews the package.
7. If approved, status changes to `approved_for_delivery`.
8. Operator delivers manually and marks as `delivered_manually`.

## Section Classification

| Pattern in Section Label | Classification |
|--------------------------|----------------|
| Contains "trace", "internal", "debug" | `internal_only` → redacted |
| Contains "sensitive", "legal", "restricted" | `restricted_sensitive` → blocked |
| Contains "operator", "decision", "action" | `operator_visible` → omitted |
| Contains "customer", "report", "summary" | `exportable_to_partner` → included |
| Other | `partner_visible` → included |

## Intake Record Rules

- `restricted_sensitive` records are always blocked.
- Records failing `can_appear_in_partner_report()` are redacted.
- Only partner-safe, redacted, or approved records are included.

## Review Gate

- Every export package starts as `draft` or `blocked`.
- Operator must explicitly call `approve_for_delivery()`.
- Only then can it be marked `delivered_manually`.
- `delivered_manually` is a recording action only — it sends nothing.

## Human Control Policy

- `ready_for_review` does not mean automatically sent.
- `approved_for_delivery` does not send anything.
- `delivered_manually` does not send anything.
- A human operator must physically deliver the package outside the repository.
