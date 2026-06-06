from __future__ import annotations

from dataclasses import dataclass, field

from src.modules.pilot_access_boundary.schemas import (
    NON_EXPORTABLE_LEVELS,
    ACTOR_VISIBLE_LEVELS,
    ActorCategory,
    VisibilityLevel,
)


@dataclass
class AccessCheckResult:
    allowed: bool
    reason: str | None = None


@dataclass
class RedactionResult:
    original_visibility: VisibilityLevel
    export_allowed: bool
    safe_sections: list[str] = field(default_factory=list)
    redacted_sections: list[str] = field(default_factory=list)
    reason: str | None = None


def can_actor_view(actor: ActorCategory, visibility: VisibilityLevel) -> AccessCheckResult:
    allowed_levels = ACTOR_VISIBLE_LEVELS.get(actor, set())
    if visibility in allowed_levels:
        return AccessCheckResult(allowed=True)
    return AccessCheckResult(
        allowed=False,
        reason=f"{actor.value} cannot view {visibility.value}",
    )


def can_export_to_partner(visibility: VisibilityLevel) -> AccessCheckResult:
    if visibility in NON_EXPORTABLE_LEVELS:
        return AccessCheckResult(
            allowed=False,
            reason=f"Visibility level '{visibility.value}' is not exportable to partner",
        )
    return AccessCheckResult(allowed=True)


def is_internal_only(visibility: VisibilityLevel) -> bool:
    return visibility == VisibilityLevel.internal_only


def should_redact(actor: ActorCategory, visibility: VisibilityLevel) -> AccessCheckResult:
    if visibility == VisibilityLevel.restricted_sensitive and actor != ActorCategory.admin:
        return AccessCheckResult(
            allowed=True,
            reason=f"Restricted sensitive content redacted for {actor.value}",
        )
    return AccessCheckResult(allowed=False)


def apply_export_redaction(
    visibility: VisibilityLevel,
    *,
    sections: dict[str, str] | None = None,
    actor: ActorCategory = ActorCategory.design_partner_viewer,
) -> RedactionResult:
    export_check = can_export_to_partner(visibility)
    if export_check.allowed:
        return RedactionResult(
            original_visibility=visibility,
            export_allowed=True,
            safe_sections=list(sections.keys()) if sections else [],
            redacted_sections=[],
        )
    if sections:
        safe = []
        redacted = []
        for label, _content in sections.items():
            if visibility in NON_EXPORTABLE_LEVELS:
                redacted.append(label)
            else:
                safe.append(label)
        return RedactionResult(
            original_visibility=visibility,
            export_allowed=False,
            safe_sections=safe,
            redacted_sections=redacted,
            reason=f"Export blocked: visibility={visibility.value}, redacted={len(redacted)} section(s)",
        )
    return RedactionResult(
        original_visibility=visibility,
        export_allowed=False,
        reason=f"Export blocked: visibility={visibility.value}",
    )


def default_visibility_for_artifact(artifact_type: str) -> VisibilityLevel:
    from src.modules.pilot_access_boundary.schemas import DEFAULT_ARTIFACT_VISIBILITY

    return DEFAULT_ARTIFACT_VISIBILITY.get(artifact_type, VisibilityLevel.internal_only)
