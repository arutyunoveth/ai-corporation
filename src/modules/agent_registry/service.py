import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.agent_registry.models import AgentRegistryRecord, AgentRegistrySet
from src.modules.agent_registry.schemas import BuildAgentRegistryRequest
from src.modules.event_log.service import append_event_record
from src.modules.prompt_schema_library.models import AgentPromptLink
from src.shared.db.base import utcnow
from src.shared.enums import AgentActivationState, AgentLifecycleStatus, AgentRegistryStatus, EventSeverity
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_agent_registry_id, next_agent_registry_set_id
from src.shared.validation import require_non_empty


def _slugify_agent_key(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    return normalized or "agent-profile"


def _resolve_agent_label(entry) -> str:
    return require_non_empty(entry.agent_role_name or entry.agent_label, "agent_role_name")


def _resolve_agent_key(entry, agent_label: str) -> str:
    candidate = entry.agent_key or _slugify_agent_key(agent_label)
    return require_non_empty(candidate, "agent_key")


def _resolve_owner_role(entry) -> str:
    return require_non_empty(entry.owner_operator or entry.owner_role, "owner_operator")


def _resolve_reviewer_role(entry, owner_role: str) -> str:
    return require_non_empty(entry.reviewer_role or entry.owner_operator or owner_role, "reviewer_role")


def _resolve_activation_state(entry) -> AgentActivationState:
    if entry.activation_state is not None:
        return entry.activation_state
    if entry.lifecycle_status is not None:
        return AgentActivationState(entry.lifecycle_status)
    return AgentActivationState.REVIEWED


def _resolve_allowed_capabilities(entry) -> list[str]:
    if entry.allowed_action_classes:
        return entry.allowed_action_classes
    if entry.allowed_capabilities_json:
        return entry.allowed_capabilities_json
    return entry.capability_tags


def _resolve_blocked_capabilities(entry) -> list[str]:
    if entry.forbidden_action_classes:
        return entry.forbidden_action_classes
    return entry.blocked_capabilities_json


def _resolve_notes(entry) -> str | None:
    return entry.description or entry.notes


def _get_set(session: Session, agent_registry_set_id: str) -> AgentRegistrySet:
    record = session.scalar(
        select(AgentRegistrySet).where(AgentRegistrySet.agent_registry_set_id == agent_registry_set_id)
    )
    if not record:
        raise NotFoundError(f"Agent registry set '{agent_registry_set_id}' was not found")
    return record


def _get_record(session: Session, agent_registry_id: str) -> AgentRegistryRecord:
    record = session.scalar(select(AgentRegistryRecord).where(AgentRegistryRecord.agent_registry_id == agent_registry_id))
    if not record:
        raise NotFoundError(f"Agent registry record '{agent_registry_id}' was not found")
    return record


def _get_records(session: Session, agent_registry_set_id: str) -> list[AgentRegistryRecord]:
    return list(
        session.scalars(
            select(AgentRegistryRecord)
            .where(AgentRegistryRecord.agent_registry_set_id == agent_registry_set_id)
            .order_by(AgentRegistryRecord.created_at.asc(), AgentRegistryRecord.id.asc())
        )
    )


def _get_links(session: Session, agent_registry_id: str) -> list[AgentPromptLink]:
    return list(
        session.scalars(
            select(AgentPromptLink)
            .where(AgentPromptLink.agent_registry_id == agent_registry_id)
            .order_by(AgentPromptLink.created_at.asc(), AgentPromptLink.id.asc())
        )
    )


def build_agent_registry(session: Session, payload: BuildAgentRegistryRequest) -> AgentRegistrySet:
    if not payload.entries:
        raise ValidationError("Agent registry build requires at least one entry")

    registry_set = AgentRegistrySet(
        agent_registry_set_id=next_agent_registry_set_id(session, AgentRegistrySet.agent_registry_set_id),
        registry_scope=require_non_empty(payload.registry_scope, "registry_scope"),
        registry_status=AgentRegistryStatus.BUILT,
    )
    session.add(registry_set)
    session.flush()

    try:
        append_event_record(
            session,
            deal_id=None,
            event_code="agent_registry_set_created",
            source_module_id="M-049",
            severity=EventSeverity.INFO,
            payload_json={"agent_registry_set_id": registry_set.agent_registry_set_id},
        )

        seen_keys: set[str] = set()
        for entry in payload.entries:
            agent_label = _resolve_agent_label(entry)
            agent_key = _resolve_agent_key(entry, agent_label)
            if agent_key in seen_keys:
                raise ValidationError(f"Duplicate agent_key '{agent_key}' in request")
            seen_keys.add(agent_key)
            owner_role = _resolve_owner_role(entry)
            reviewer_role = _resolve_reviewer_role(entry, owner_role)
            activation_state = _resolve_activation_state(entry)
            allowed_capabilities = _resolve_allowed_capabilities(entry)
            blocked_capabilities = _resolve_blocked_capabilities(entry)
            notes = _resolve_notes(entry)

            record = AgentRegistryRecord(
                agent_registry_id=next_agent_registry_id(session, AgentRegistryRecord.agent_registry_id),
                agent_registry_set_id=registry_set.agent_registry_set_id,
                agent_key=agent_key,
                agent_label=agent_label,
                owner_role=owner_role,
                reviewer_role=reviewer_role,
                activation_state=activation_state,
                approval_reference=entry.approval_reference.strip() if entry.approval_reference else None,
                allowed_capabilities_json=allowed_capabilities,
                blocked_capabilities_json=blocked_capabilities,
                notes=notes.strip() if notes else None,
                agent_scope=entry.agent_scope,
                agent_kind=entry.agent_kind,
                reports_to=entry.reports_to,
                data_policy=entry.data_policy,
                runtime_mode=entry.runtime_mode,
                model_tier=entry.model_tier,
                description=entry.description.strip() if entry.description else None,
                responsibilities_json=entry.responsibilities,
                inputs_json=entry.inputs,
                outputs_json=entry.outputs,
                escalation_rules_json=entry.escalation_rules,
                forbidden_actions_json=entry.forbidden_actions,
            )
            session.add(record)
            session.flush()
            append_event_record(
                session,
                deal_id=None,
                event_code="agent_registry_record_created",
                source_module_id="M-049",
                severity=EventSeverity.INFO,
                payload_json={
                    "agent_registry_set_id": registry_set.agent_registry_set_id,
                    "agent_registry_id": record.agent_registry_id,
                    "agent_key": record.agent_key,
                    "agent_role_name": record.agent_label,
                    "lifecycle_status": str(record.activation_state),
                    "agent_scope": record.agent_scope,
                },
            )

        registry_set.updated_at = utcnow()
        session.add(registry_set)
        append_event_record(
            session,
            deal_id=None,
            event_code="agent_registry_status_changed",
            source_module_id="M-049",
            severity=EventSeverity.INFO,
            payload_json={
                "agent_registry_set_id": registry_set.agent_registry_set_id,
                "registry_status": str(registry_set.registry_status),
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        append_event_record(
            session,
            deal_id=None,
            event_code="agent_registry_failed",
            source_module_id="M-049",
            severity=EventSeverity.HIGH,
            payload_json={
                "agent_registry_set_id": registry_set.agent_registry_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise

    session.refresh(registry_set)
    return registry_set


def get_agent_registry_set(
    session: Session,
    agent_registry_set_id: str,
) -> tuple[AgentRegistrySet, list[tuple[AgentRegistryRecord, list[AgentPromptLink]]]]:
    registry_set = _get_set(session, agent_registry_set_id)
    records = _get_records(session, agent_registry_set_id)
    return registry_set, [(record, _get_links(session, record.agent_registry_id)) for record in records]


def list_agent_registry_sets(
    session: Session,
    *,
    registry_scope: str | None = None,
) -> list[tuple[AgentRegistrySet, list[tuple[AgentRegistryRecord, list[AgentPromptLink]]]]]:
    query = select(AgentRegistrySet).order_by(AgentRegistrySet.created_at.desc(), AgentRegistrySet.id.desc())
    if registry_scope:
        query = query.where(AgentRegistrySet.registry_scope == registry_scope.strip())
    records = list(session.scalars(query))
    return [get_agent_registry_set(session, item.agent_registry_set_id) for item in records]


def get_agent_registry_record(
    session: Session,
    agent_registry_id: str,
) -> tuple[AgentRegistryRecord, list[AgentPromptLink]]:
    record = _get_record(session, agent_registry_id)
    return record, _get_links(session, record.agent_registry_id)
