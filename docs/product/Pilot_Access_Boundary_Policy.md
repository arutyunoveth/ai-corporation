# Pilot Access Boundary Policy

## Purpose

This document defines the minimal access boundary for design-partner pilot usage. It ensures that internal operator actions, restricted notes, and sensitive traces are clearly distinguished from partner-visible and exportable artifacts.

## Important Disclaimers

- **This is a pilot boundary, not production auth.**
- **This does not replace proper SaaS authentication or enterprise RBAC.**
- **This is meant to prevent accidental leakage in reports/exports.**
- **Production auth/access hardening remains in backlog.**

## Visibility Levels

| Level | Meaning | Exportable? |
|-------|---------|-------------|
| `internal_only` | Internal system traces, metadata records | No |
| `operator_visible` | Operator actions, decisions, blockers | No |
| `partner_visible` | Partner-safe evidence, metrics | Yes |
| `exportable_to_partner` | Customer reports after human review | Yes |
| `restricted_sensitive` | Legal-sensitive notes, flagged content | No (admin only) |

## Actor Categories

| Category | Default Access |
|----------|----------------|
| `system` | All non-restricted |
| `internal_operator` | `operator_visible`, `partner_visible` |
| `reviewer` | `operator_visible`, `partner_visible` |
| `design_partner_viewer` | `partner_visible`, `exportable_to_partner` |
| `admin` | All levels |

## Default Artifact Visibility

| Artifact Type | Default Visibility |
|---------------|-------------------|
| `operator_decision` | `operator_visible` |
| `operator_action` | `operator_visible` |
| `runtime_trace` | `internal_only` |
| `pilot_evidence` | `partner_visible` |
| `prebid_report` | `operator_visible` |
| `customer_report` | `exportable_to_partner` |
| `sensitive_note` | `restricted_sensitive` |
| `blocker_record` | `operator_visible` |
| `metrics_record` | `partner_visible` |

## Export Rules

1. `restricted_sensitive` artifacts are **always blocked** from partner export.
2. `internal_only` sections are **omitted/redacted** from partner-facing output.
3. `operator_visible` artifacts are **not exported** to partners.
4. `partner_visible` and `exportable_to_partner` artifacts **may be exported**.
5. Customer reports default to `exportable_to_partner` but require **human review** before export.
6. The export guard returns a clear result describing what was included and excluded.

## Usage

```python
from src.modules.pilot_access_boundary.schemas import ActorCategory, VisibilityLevel
from src.modules.pilot_access_boundary.service import (
    can_actor_view, can_export_to_partner, apply_export_redaction,
)

# Check if partner can view a runtime trace
result = can_actor_view(ActorCategory.design_partner_viewer, VisibilityLevel.internal_only)
# result.allowed == False

# Check if a report is exportable
result = can_export_to_partner(VisibilityLevel.exportable_to_partner)
# result.allowed == True

# Apply redaction for export
result = apply_export_redaction(VisibilityLevel.internal_only, sections={
    "trace": "...", "summary": "..."
})
# result.export_allowed == False
# result.redacted_sections == ["trace", "summary"]
```

## Enforced In

- All customer-facing export/report paths should call `apply_export_redaction` or `can_export_to_partner` before delivery.
- All artifact rendering in partner-facing views should call `can_actor_view` to filter displayed sections.
