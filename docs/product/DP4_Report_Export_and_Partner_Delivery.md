# Sprint DP4 — Report Export and Partner Delivery

## Scope

Create a safe partner-facing export/delivery flow for reports and pilot artifacts.

This is not a customer portal and not external delivery automation.
It is an internal export package generator with access-boundary/redaction enforcement.

## Deliverables

1. Export package schema with status lifecycle.
2. Export generator that applies DP1 export guard and DP3 redaction rules.
3. Markdown and JSON output formats.
4. Manual delivery marker (`delivered_manually` — does not send anything).
5. Docs: sprint spec, export policy, manual delivery checklist.
6. Tests covering export generation, redaction, blocking, delivery marker.

## Export Statuses

- `draft`, `blocked`, `ready_for_review`, `approved_for_delivery`, `delivered_manually`, `archived`

## Acceptance Criteria

1. Export package generation includes only partner-safe sections.
2. `internal_only` sections are omitted/redacted.
3. `restricted_sensitive` sections are blocked.
4. `operator_visible` sections are omitted from partner package.
5. `exportable_to_partner` and `partner_visible` sections are included.
6. Human review required before `approved_for_delivery`.
7. `delivered_manually` does not send external messages.
8. Export summary lists included/excluded sections.

## Non-Goals

- No automated email.
- No customer portal.
- No PDF unless already trivial.
- No external file delivery.
- No e-sign.
- No legal delivery guarantee.

## Roadmap / Master Plan Alignment

- Current repository phase: `Design-Partner Pilot Stage`
- Sprint phase: `DP4 — Report Export and Partner Delivery`
- Master Plan section: `Safe partner-facing export/delivery flow`
- Scope implemented: export package generator, redaction enforcement, delivery marker
- Explicit non-goals preserved: no automated email, no customer portal, no external delivery
- Deferred items not touched: procurement integration, supplier automation, EDS/signature, SaaS hardening
- Tests proving alignment: targeted DP4 tests + DP1/DP2/DP3 tests + full pytest
- Docs updated: this sprint spec, Partner_Report_Export_Policy.md, Manual_Delivery_Checklist.md, Operator_Runbook_MVP_v1.md, Product_Backlog.md
