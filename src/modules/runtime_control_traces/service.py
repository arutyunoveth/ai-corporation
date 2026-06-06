from sqlalchemy import select
from sqlalchemy.orm import Session

from src.modules.agent_registry.models import AgentRegistryRecord
from src.modules.event_log.service import append_event_record
from src.modules.prompt_schema_library.models import PromptSchemaRecord
from src.modules.runtime_control_traces.models import RuntimeControlTrace
from src.modules.runtime_control_traces.schemas import (
    CreateRuntimeControlTraceRequest,
    UpdateRuntimeControlTraceReviewRequest,
)
from src.shared.db.base import utcnow
from src.shared.enums import EventSeverity, HumanReviewStatus
from src.shared.errors import NotFoundError, ValidationError
from src.shared.ids import next_runtime_trace_id
from src.shared.validation import require_non_empty


TRACE_SOURCE_MODULE = "runtime_control_trace_ledger"


def _get_trace(session: Session, runtime_trace_id: str) -> RuntimeControlTrace:
    trace = session.scalar(
        select(RuntimeControlTrace).where(RuntimeControlTrace.runtime_trace_id == runtime_trace_id)
    )
    if not trace:
        raise NotFoundError(f"Runtime control trace '{runtime_trace_id}' was not found")
    return trace


def _validate_refs(session: Session, payload: CreateRuntimeControlTraceRequest) -> None:
    if payload.prompt_schema_ref:
        prompt = session.scalar(
            select(PromptSchemaRecord).where(PromptSchemaRecord.prompt_schema_id == payload.prompt_schema_ref)
        )
        if not prompt:
            raise ValidationError(f"Prompt/schema record '{payload.prompt_schema_ref}' does not exist")

    if payload.agent_profile_ref:
        agent = session.scalar(
            select(AgentRegistryRecord).where(AgentRegistryRecord.agent_registry_id == payload.agent_profile_ref)
        )
        if not agent:
            raise ValidationError(f"Agent registry record '{payload.agent_profile_ref}' does not exist")


def create_runtime_control_trace(
    session: Session,
    payload: CreateRuntimeControlTraceRequest,
) -> RuntimeControlTrace:
    _validate_refs(session, payload)

    trace = RuntimeControlTrace(
        runtime_trace_id=next_runtime_trace_id(session, RuntimeControlTrace.runtime_trace_id),
        runtime_slice=require_non_empty(payload.runtime_slice, "runtime_slice"),
        source_entity=require_non_empty(payload.source_entity, "source_entity"),
        actor_type=payload.actor_type,
        actor_ref=require_non_empty(payload.actor_ref, "actor_ref"),
        action_type=payload.action_type,
        target_module=payload.target_module.strip() if payload.target_module else None,
        target_record_id=payload.target_record_id.strip() if payload.target_record_id else None,
        prompt_schema_ref=payload.prompt_schema_ref,
        agent_profile_ref=payload.agent_profile_ref,
        input_artifact_ref=payload.input_artifact_ref.strip() if payload.input_artifact_ref else None,
        output_artifact_ref=payload.output_artifact_ref.strip() if payload.output_artifact_ref else None,
        input_summary=payload.input_summary.strip() if payload.input_summary else None,
        output_summary=payload.output_summary.strip() if payload.output_summary else None,
        validation_status=payload.validation_status,
        human_review_status=payload.human_review_status,
        reviewer_operator=payload.reviewer_operator.strip() if payload.reviewer_operator else None,
        final_disposition=payload.final_disposition,
    )
    session.add(trace)
    session.flush()

    append_event_record(
        session,
        deal_id=None,
        event_code="runtime_control_trace_created",
        source_module_id=TRACE_SOURCE_MODULE,
        severity=EventSeverity.INFO,
        payload_json={
            "runtime_trace_id": trace.runtime_trace_id,
            "runtime_slice": trace.runtime_slice,
            "action_type": str(trace.action_type),
            "prompt_schema_ref": trace.prompt_schema_ref,
            "agent_profile_ref": trace.agent_profile_ref,
        },
    )
    session.commit()
    session.refresh(trace)
    return trace


def get_runtime_control_trace(session: Session, runtime_trace_id: str) -> RuntimeControlTrace:
    return _get_trace(session, runtime_trace_id)


def list_runtime_control_traces(
    session: Session,
    *,
    runtime_slice: str | None = None,
) -> list[RuntimeControlTrace]:
    query = select(RuntimeControlTrace).order_by(
        RuntimeControlTrace.created_at.desc(),
        RuntimeControlTrace.id.desc(),
    )
    if runtime_slice:
        query = query.where(RuntimeControlTrace.runtime_slice == runtime_slice.strip())
    return list(session.scalars(query))


def update_runtime_control_trace_review(
    session: Session,
    runtime_trace_id: str,
    payload: UpdateRuntimeControlTraceReviewRequest,
) -> RuntimeControlTrace:
    trace = _get_trace(session, runtime_trace_id)
    trace.human_review_status = payload.human_review_status
    trace.reviewer_operator = require_non_empty(payload.reviewer_operator, "reviewer_operator")
    trace.final_disposition = payload.final_disposition
    trace.updated_at = utcnow()
    session.add(trace)

    append_event_record(
        session,
        deal_id=None,
        event_code="runtime_control_trace_review_status_changed",
        source_module_id=TRACE_SOURCE_MODULE,
        severity=EventSeverity.INFO,
        payload_json={
            "runtime_trace_id": trace.runtime_trace_id,
            "human_review_status": str(trace.human_review_status),
            "reviewer_operator": trace.reviewer_operator,
            "final_disposition": str(trace.final_disposition) if trace.final_disposition else None,
        },
    )
    session.commit()
    session.refresh(trace)
    return trace
