# Sprint DP1 — Minimal Access Boundary

## Scope

Add a minimal internal access boundary for design-partner pilot usage without implementing full production auth, billing, SaaS tenancy, or enterprise RBAC.

This sprint creates a lightweight pilot-facing boundary so that future design-partner workflows can distinguish:
- internal operator actions;
- design-partner-visible artifacts;
- restricted/internal-only artifacts;
- exportable reports;
- non-exportable traces or sensitive notes.

## Deliverables

1. Access boundary schemas: visibility levels, actor categories, classification constants.
2. Access boundary service: rule-based actors `can_actor_view`, `can_export_to_partner`, `should_redact`, `apply_export_redaction`.
3. Redaction/export guard for customer-facing export/report paths.
4. Pilot access boundary policy doc.
5. Updated Operator Runbook with boundary notes.
6. Updated Product Backlog — mark DP1 backlog item as complete.
7. Tests for actor visibility rules, export guard, redaction, and no external action.
8. Full pytest with no regressions.

## Acceptance Criteria

1. `design_partner_viewer` can view `partner_visible` and `exportable_to_partner` artifacts.
2. `design_partner_viewer` cannot view `internal_only` or `restricted_sensitive`.
3. `internal_operator` can view `operator_visible` and `partner_visible`.
4. `admin` can view all levels.
5. `restricted_sensitive` artifacts are blocked from partner export.
6. `internal_only` traces are omitted from partner export.
7. Export guard returns a clear result explaining what was included/excluded.
8. All existing controlled pilot tests and the full suite still pass.
9. No production auth, login, session, billing, tenant isolation, or platform integration introduced.

## Non-Goals (Global Restrictions)

- No autonomous bid submission.
- No EDS/signature.
- No procurement platform integration.
- No supplier email automation.
- No uncontrolled external communication.
- No broad autonomous runtime.
- No production SaaS hardening.
- No billing.
- No post-award commercialization.
- No login/session management.
- No multi-tenant isolation.
- No production authentication.

## Roadmap / Master Plan Alignment

- Current repository phase: `Design-Partner Pilot Stage`
- Sprint phase: `DP1 — Minimal Access Boundary`
- Master Plan section: `Add minimal pilot-facing access boundary before broader customer circulation`
- Explicit non-goals preserved: no production auth, no billing, no tenant isolation, no platform integration
- Deferred items not touched: procurement integration, supplier automation, EDS/signature, SaaS hardening, broad autonomy
- Tests proving alignment: targeted DP1 tests + full `pytest`
- Docs updated: this sprint spec, Pilot_Access_Boundary_Policy.md, Operator_Runbook_MVP_v1.md, Product_Backlog.md
