from __future__ import annotations

from enum import StrEnum


class VisibilityLevel(StrEnum):
    internal_only = "internal_only"
    operator_visible = "operator_visible"
    partner_visible = "partner_visible"
    exportable_to_partner = "exportable_to_partner"
    restricted_sensitive = "restricted_sensitive"


class ActorCategory(StrEnum):
    system = "system"
    internal_operator = "internal_operator"
    reviewer = "reviewer"
    design_partner_viewer = "design_partner_viewer"
    admin = "admin"


ACTOR_VISIBLE_LEVELS: dict[ActorCategory, set[VisibilityLevel]] = {
    ActorCategory.system: {
        VisibilityLevel.internal_only,
        VisibilityLevel.operator_visible,
        VisibilityLevel.partner_visible,
        VisibilityLevel.exportable_to_partner,
    },
    ActorCategory.internal_operator: {
        VisibilityLevel.operator_visible,
        VisibilityLevel.partner_visible,
    },
    ActorCategory.reviewer: {
        VisibilityLevel.operator_visible,
        VisibilityLevel.partner_visible,
    },
    ActorCategory.design_partner_viewer: {
        VisibilityLevel.partner_visible,
        VisibilityLevel.exportable_to_partner,
    },
    ActorCategory.admin: {
        VisibilityLevel.internal_only,
        VisibilityLevel.operator_visible,
        VisibilityLevel.partner_visible,
        VisibilityLevel.exportable_to_partner,
        VisibilityLevel.restricted_sensitive,
    },
}

DEFAULT_ARTIFACT_VISIBILITY: dict[str, VisibilityLevel] = {
    "operator_decision": VisibilityLevel.operator_visible,
    "operator_action": VisibilityLevel.operator_visible,
    "runtime_trace": VisibilityLevel.internal_only,
    "pilot_evidence": VisibilityLevel.partner_visible,
    "prebid_report": VisibilityLevel.operator_visible,
    "customer_report": VisibilityLevel.exportable_to_partner,
    "sensitive_note": VisibilityLevel.restricted_sensitive,
    "blocker_record": VisibilityLevel.operator_visible,
    "metrics_record": VisibilityLevel.partner_visible,
}

EXPORTABLE_LEVELS: set[VisibilityLevel] = {
    VisibilityLevel.exportable_to_partner,
    VisibilityLevel.partner_visible,
}

NON_EXPORTABLE_LEVELS: set[VisibilityLevel] = {
    VisibilityLevel.internal_only,
    VisibilityLevel.restricted_sensitive,
    VisibilityLevel.operator_visible,
}
