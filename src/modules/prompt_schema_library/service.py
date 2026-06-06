from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.agent_registry.models import AgentRegistryRecord
from src.modules.event_log.service import append_event_record
from src.modules.prompt_schema_library.models import AgentPromptLink, PromptSchemaLibrarySet, PromptSchemaRecord
from src.modules.prompt_schema_library.schemas import BuildPromptSchemaLibraryRequest
from src.shared.db.base import utcnow
from src.shared.enums import AgentPromptLinkStatus, EventSeverity, PromptSchemaLibraryStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_prompt_schema_id, next_prompt_schema_library_set_id
from src.shared.validation import require_non_empty


def _get_set(session: Session, prompt_schema_library_set_id: str) -> PromptSchemaLibrarySet:
    record = session.scalar(
        select(PromptSchemaLibrarySet).where(
            PromptSchemaLibrarySet.prompt_schema_library_set_id == prompt_schema_library_set_id
        )
    )
    if not record:
        raise NotFoundError(f"Prompt/schema library set '{prompt_schema_library_set_id}' was not found")
    return record


def _get_record(session: Session, prompt_schema_id: str) -> PromptSchemaRecord:
    record = session.scalar(select(PromptSchemaRecord).where(PromptSchemaRecord.prompt_schema_id == prompt_schema_id))
    if not record:
        raise NotFoundError(f"Prompt/schema record '{prompt_schema_id}' was not found")
    return record


def _get_records(session: Session, prompt_schema_library_set_id: str) -> list[PromptSchemaRecord]:
    return list(
        session.scalars(
            select(PromptSchemaRecord)
            .where(PromptSchemaRecord.prompt_schema_library_set_id == prompt_schema_library_set_id)
            .order_by(PromptSchemaRecord.created_at.asc(), PromptSchemaRecord.id.asc())
        )
    )


def _get_links(session: Session, prompt_schema_id: str) -> list[AgentPromptLink]:
    return list(
        session.scalars(
            select(AgentPromptLink)
            .where(AgentPromptLink.prompt_schema_id == prompt_schema_id)
            .order_by(AgentPromptLink.created_at.asc(), AgentPromptLink.id.asc())
        )
    )


def build_prompt_schema_library(session: Session, payload: BuildPromptSchemaLibraryRequest) -> PromptSchemaLibrarySet:
    if not payload.assets:
        raise ValidationError("Prompt/schema library build requires at least one asset")

    library_set = PromptSchemaLibrarySet(
        prompt_schema_library_set_id=next_prompt_schema_library_set_id(
            session,
            PromptSchemaLibrarySet.prompt_schema_library_set_id,
        ),
        library_scope=require_non_empty(payload.library_scope, "library_scope"),
        library_status=PromptSchemaLibraryStatus.BUILT,
    )
    session.add(library_set)
    session.flush()

    try:
        append_event_record(
            session,
            deal_id=None,
            event_code="prompt_schema_library_set_created",
            source_module_id="M-050",
            severity=EventSeverity.INFO,
            payload_json={"prompt_schema_library_set_id": library_set.prompt_schema_library_set_id},
        )

        seen_assets: set[tuple[str, str]] = set()
        for asset in payload.assets:
            asset_key = require_non_empty(asset.asset_key, "asset_key")
            version_tag = require_non_empty(asset.version_tag, "version_tag")
            asset_pair = (asset_key, version_tag)
            if asset_pair in seen_assets:
                raise ValidationError(f"Duplicate asset_key/version_tag pair '{asset_key}:{version_tag}' in request")
            seen_assets.add(asset_pair)

            record = PromptSchemaRecord(
                prompt_schema_id=next_prompt_schema_id(session, PromptSchemaRecord.prompt_schema_id),
                prompt_schema_library_set_id=library_set.prompt_schema_library_set_id,
                asset_key=asset_key,
                asset_type=asset.asset_type,
                version_tag=version_tag,
                owner_role=require_non_empty(asset.owner_role, "owner_role"),
                reviewer_role=require_non_empty(asset.reviewer_role, "reviewer_role"),
                asset_status=asset.asset_status,
                usage_constraints_text=require_non_empty(asset.usage_constraints_text, "usage_constraints_text"),
                input_schema_ref=asset.input_schema_ref.strip() if asset.input_schema_ref else None,
                output_schema_ref=asset.output_schema_ref.strip() if asset.output_schema_ref else None,
                safety_notes=asset.safety_notes.strip() if asset.safety_notes else None,
                asset_payload_json=asset.asset_payload_json,
            )
            session.add(record)
            session.flush()
            append_event_record(
                session,
                deal_id=None,
                event_code="prompt_schema_record_created",
                source_module_id="M-050",
                severity=EventSeverity.INFO,
                payload_json={
                    "prompt_schema_library_set_id": library_set.prompt_schema_library_set_id,
                    "prompt_schema_id": record.prompt_schema_id,
                    "asset_key": record.asset_key,
                },
            )

            for agent_registry_id in asset.linked_agent_registry_ids:
                agent = session.scalar(
                    select(AgentRegistryRecord).where(AgentRegistryRecord.agent_registry_id == agent_registry_id)
                )
                if not agent:
                    raise ValidationError(f"Agent registry record '{agent_registry_id}' does not exist")
                existing_link = session.scalar(
                    select(AgentPromptLink).where(
                        AgentPromptLink.agent_registry_id == agent_registry_id,
                        AgentPromptLink.prompt_schema_id == record.prompt_schema_id,
                    )
                )
                if existing_link:
                    continue
                session.add(
                    AgentPromptLink(
                        agent_registry_id=agent_registry_id,
                        prompt_schema_id=record.prompt_schema_id,
                        link_status=AgentPromptLinkStatus.APPROVED,
                    )
                )
                session.flush()
                append_event_record(
                    session,
                    deal_id=None,
                    event_code="agent_prompt_link_created",
                    source_module_id="M-050",
                    severity=EventSeverity.INFO,
                    payload_json={
                        "agent_registry_id": agent_registry_id,
                        "prompt_schema_id": record.prompt_schema_id,
                    },
                )

        library_set.updated_at = utcnow()
        session.add(library_set)
        append_event_record(
            session,
            deal_id=None,
            event_code="prompt_schema_status_changed",
            source_module_id="M-050",
            severity=EventSeverity.INFO,
            payload_json={
                "prompt_schema_library_set_id": library_set.prompt_schema_library_set_id,
                "library_status": str(library_set.library_status),
            },
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        append_event_record(
            session,
            deal_id=None,
            event_code="prompt_schema_failed",
            source_module_id="M-050",
            severity=EventSeverity.HIGH,
            payload_json={
                "prompt_schema_library_set_id": library_set.prompt_schema_library_set_id,
                "error": str(exc),
            },
        )
        session.commit()
        raise

    session.refresh(library_set)
    return library_set


def get_prompt_schema_library_set(
    session: Session,
    prompt_schema_library_set_id: str,
) -> tuple[PromptSchemaLibrarySet, list[tuple[PromptSchemaRecord, list[AgentPromptLink]]]]:
    library_set = _get_set(session, prompt_schema_library_set_id)
    records = _get_records(session, prompt_schema_library_set_id)
    return library_set, [(record, _get_links(session, record.prompt_schema_id)) for record in records]


def list_prompt_schema_library_sets(
    session: Session,
    *,
    library_scope: str | None = None,
) -> list[tuple[PromptSchemaLibrarySet, list[tuple[PromptSchemaRecord, list[AgentPromptLink]]]]]:
    query = select(PromptSchemaLibrarySet).order_by(
        PromptSchemaLibrarySet.created_at.desc(),
        PromptSchemaLibrarySet.id.desc(),
    )
    if library_scope:
        query = query.where(PromptSchemaLibrarySet.library_scope == library_scope.strip())
    sets = list(session.scalars(query))
    return [get_prompt_schema_library_set(session, item.prompt_schema_library_set_id) for item in sets]


def get_prompt_schema_record(
    session: Session,
    prompt_schema_id: str,
) -> tuple[PromptSchemaRecord, list[AgentPromptLink]]:
    record = _get_record(session, prompt_schema_id)
    return record, _get_links(session, record.prompt_schema_id)
