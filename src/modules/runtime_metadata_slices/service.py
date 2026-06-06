from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.agent_registry.models import AgentRegistryRecord
from src.modules.event_log.service import append_event_record
from src.modules.prompt_schema_library.models import PromptSchemaRecord
from src.modules.runtime_control_traces.models import RuntimeControlTrace
from src.modules.runtime_metadata_slices.models import RuntimeMetadataSlice
from src.modules.runtime_metadata_slices.schemas import (
    CreateRuntimeMetadataSliceRequest,
    UpdateRuntimeMetadataSliceReviewRequest,
)
from src.shared.db.base import utcnow
from src.shared.enums import (
    EventSeverity,
    RuntimeTraceActionType,
    RuntimeTraceActorType,
    RuntimeTraceDisposition,
    RuntimeTraceValidationStatus,
)
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_runtime_metadata_slice_id, next_runtime_trace_id
from src.shared.validation import require_non_empty


SLICE_SOURCE_MODULE = "runtime_metadata_slice"


def _normalize_contexts(values: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        value = require_non_empty(item, "runtime_context").upper()
        if value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


def _get_slice(session: Session, runtime_metadata_slice_id: str) -> RuntimeMetadataSlice:
    runtime_slice = session.scalar(
        select(RuntimeMetadataSlice).where(
            RuntimeMetadataSlice.runtime_metadata_slice_id == runtime_metadata_slice_id
        )
    )
    if not runtime_slice:
        raise NotFoundError(f"Runtime metadata slice '{runtime_metadata_slice_id}' was not found")
    return runtime_slice


def _validate_create_refs(session: Session, payload: CreateRuntimeMetadataSliceRequest) -> tuple[list[str], list[str]]:
    agent = session.scalar(
        select(AgentRegistryRecord).where(AgentRegistryRecord.agent_registry_id == payload.linked_agent_profile_id)
    )
    if not agent:
        raise ValidationError(f"Agent registry record '{payload.linked_agent_profile_id}' does not exist")

    prompt = session.scalar(
        select(PromptSchemaRecord).where(PromptSchemaRecord.prompt_schema_id == payload.linked_prompt_schema_id)
    )
    if not prompt:
        raise ValidationError(f"Prompt/schema record '{payload.linked_prompt_schema_id}' does not exist")

    allowed = _normalize_contexts(payload.allowed_runtime_contexts)
    forbidden = _normalize_contexts(payload.forbidden_runtime_contexts)
    overlap = set(allowed) & set(forbidden)
    if overlap:
        raise ValidationError(
            "Runtime metadata slice contains overlapping allowed and forbidden runtime contexts: "
            + ", ".join(sorted(overlap))
        )

    for trace_ref in payload.trace_refs:
        trace = session.scalar(
            select(RuntimeControlTrace).where(RuntimeControlTrace.runtime_trace_id == trace_ref)
        )
        if not trace:
            raise ValidationError(f"Runtime control trace '{trace_ref}' does not exist")

    return allowed, forbidden


def _create_trace_record(
    session: Session,
    *,
    runtime_slice: str,
    linked_agent_profile_id: str,
    linked_prompt_schema_id: str,
    target_record_id: str,
    output_summary: str,
    review_status,
) -> RuntimeControlTrace:
    trace = RuntimeControlTrace(
        runtime_trace_id=next_runtime_trace_id(session, RuntimeControlTrace.runtime_trace_id),
        runtime_slice=runtime_slice,
        source_entity="runtime_metadata_slice",
        actor_type=RuntimeTraceActorType.AGENT_PROFILE,
        actor_ref=linked_agent_profile_id,
        action_type=RuntimeTraceActionType.LINK_METADATA,
        target_module="MVP_RUNTIME_PHASE_1",
        target_record_id=target_record_id,
        prompt_schema_ref=linked_prompt_schema_id,
        agent_profile_ref=linked_agent_profile_id,
        input_summary="Metadata slice linkage requested.",
        output_summary=output_summary,
        validation_status=RuntimeTraceValidationStatus.PASSED,
        human_review_status=review_status,
        final_disposition=RuntimeTraceDisposition.NEEDS_HUMAN_REVIEW,
    )
    session.add(trace)
    session.flush()
    append_event_record(
        session,
        deal_id=None,
        event_code="runtime_control_trace_created",
        source_module_id=SLICE_SOURCE_MODULE,
        severity=EventSeverity.INFO,
        payload_json={
            "runtime_trace_id": trace.runtime_trace_id,
            "runtime_slice": runtime_slice,
            "target_record_id": target_record_id,
        },
    )
    return trace


def create_runtime_metadata_slice(
    session: Session,
    payload: CreateRuntimeMetadataSliceRequest,
) -> RuntimeMetadataSlice:
    allowed, forbidden = _validate_create_refs(session, payload)
    runtime_slice = RuntimeMetadataSlice(
        runtime_metadata_slice_id=next_runtime_metadata_slice_id(
            session,
            RuntimeMetadataSlice.runtime_metadata_slice_id,
        ),
        runtime_slice=require_non_empty(payload.runtime_slice, "runtime_slice"),
        linked_agent_profile_id=payload.linked_agent_profile_id,
        linked_prompt_schema_id=payload.linked_prompt_schema_id,
        allowed_runtime_contexts=allowed,
        forbidden_runtime_contexts=forbidden,
        review_status=payload.review_status,
        trace_refs_json=list(payload.trace_refs),
        notes=payload.notes.strip() if payload.notes else None,
    )
    session.add(runtime_slice)
    session.flush()

    trace = _create_trace_record(
        session,
        runtime_slice=runtime_slice.runtime_slice,
        linked_agent_profile_id=runtime_slice.linked_agent_profile_id,
        linked_prompt_schema_id=runtime_slice.linked_prompt_schema_id,
        target_record_id=runtime_slice.runtime_metadata_slice_id,
        output_summary="Runtime metadata slice created.",
        review_status=runtime_slice.review_status,
    )
    runtime_slice.trace_refs_json = [*runtime_slice.trace_refs_json, trace.runtime_trace_id]
    runtime_slice.updated_at = utcnow()
    session.add(runtime_slice)

    append_event_record(
        session,
        deal_id=None,
        event_code="runtime_metadata_slice_created",
        source_module_id=SLICE_SOURCE_MODULE,
        severity=EventSeverity.INFO,
        payload_json={
            "runtime_metadata_slice_id": runtime_slice.runtime_metadata_slice_id,
            "linked_agent_profile_id": runtime_slice.linked_agent_profile_id,
            "linked_prompt_schema_id": runtime_slice.linked_prompt_schema_id,
        },
    )
    session.commit()
    session.refresh(runtime_slice)
    return runtime_slice


def get_runtime_metadata_slice(session: Session, runtime_metadata_slice_id: str) -> RuntimeMetadataSlice:
    return _get_slice(session, runtime_metadata_slice_id)


def list_runtime_metadata_slices(
    session: Session,
    *,
    runtime_slice: str | None = None,
) -> list[RuntimeMetadataSlice]:
    query = select(RuntimeMetadataSlice).order_by(
        RuntimeMetadataSlice.created_at.desc(),
        RuntimeMetadataSlice.id.desc(),
    )
    if runtime_slice:
        query = query.where(RuntimeMetadataSlice.runtime_slice == runtime_slice.strip())
    return list(session.scalars(query))


def update_runtime_metadata_slice_review(
    session: Session,
    runtime_metadata_slice_id: str,
    payload: UpdateRuntimeMetadataSliceReviewRequest,
) -> RuntimeMetadataSlice:
    runtime_slice = _get_slice(session, runtime_metadata_slice_id)
    runtime_slice.review_status = payload.review_status
    if payload.notes:
        runtime_slice.notes = payload.notes.strip()
    runtime_slice.updated_at = utcnow()
    session.add(runtime_slice)

    trace = _create_trace_record(
        session,
        runtime_slice=runtime_slice.runtime_slice,
        linked_agent_profile_id=runtime_slice.linked_agent_profile_id,
        linked_prompt_schema_id=runtime_slice.linked_prompt_schema_id,
        target_record_id=runtime_slice.runtime_metadata_slice_id,
        output_summary="Runtime metadata slice review status updated.",
        review_status=runtime_slice.review_status,
    )
    runtime_slice.trace_refs_json = [*runtime_slice.trace_refs_json, trace.runtime_trace_id]
    session.add(runtime_slice)

    append_event_record(
        session,
        deal_id=None,
        event_code="runtime_metadata_slice_review_status_changed",
        source_module_id=SLICE_SOURCE_MODULE,
        severity=EventSeverity.INFO,
        payload_json={
            "runtime_metadata_slice_id": runtime_slice.runtime_metadata_slice_id,
            "review_status": str(runtime_slice.review_status),
        },
    )
    session.commit()
    session.refresh(runtime_slice)
    return runtime_slice
