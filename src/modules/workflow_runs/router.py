from fastapi import APIRouter, Query, status

from src.modules.workflow_runs.schemas import (
    BuildWorkflowRunRequest,
    WorkflowRunRecordResponse,
    WorkflowRunSetResponse,
    WorkflowStepRecordResponse,
)
from src.modules.workflow_runs.service import (
    build_workflow_run,
    get_workflow_run_record,
    get_workflow_run_set,
    list_workflow_run_sets,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkflowScopeType

router = APIRouter(tags=["workflow-runs"])


def _to_step_response(item) -> WorkflowStepRecordResponse:
    return WorkflowStepRecordResponse.model_validate(item)


def _to_record_response(result: tuple) -> WorkflowRunRecordResponse:
    record, steps = result
    return WorkflowRunRecordResponse(
        workflow_run_id=record.workflow_run_id,
        workflow_run_set_id=record.workflow_run_set_id,
        summary_text=record.summary_text,
        current_phase=record.current_phase,
        created_at=record.created_at,
        updated_at=record.updated_at,
        steps=[_to_step_response(item) for item in steps],
    )


def _to_set_response(result: tuple) -> WorkflowRunSetResponse:
    workflow_set, records = result
    return WorkflowRunSetResponse(
        workflow_run_set_id=workflow_set.workflow_run_set_id,
        scope_type=workflow_set.scope_type,
        scope_ref=workflow_set.scope_ref,
        workflow_status=workflow_set.workflow_status,
        created_at=workflow_set.created_at,
        updated_at=workflow_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/workflow-runs/build", response_model=WorkflowRunSetResponse, status_code=status.HTTP_201_CREATED)
def build_workflow_run_route(payload: BuildWorkflowRunRequest, session: DBSession) -> WorkflowRunSetResponse:
    workflow_set = build_workflow_run(session, payload)
    return _to_set_response(get_workflow_run_set(session, workflow_set.workflow_run_set_id))


@router.get("/workflow-runs/{workflow_run_set_id}", response_model=WorkflowRunSetResponse)
def get_workflow_run_set_route(workflow_run_set_id: str, session: DBSession) -> WorkflowRunSetResponse:
    return _to_set_response(get_workflow_run_set(session, workflow_run_set_id))


@router.get("/workflow-runs", response_model=list[WorkflowRunSetResponse])
def list_workflow_run_sets_route(
    session: DBSession,
    scope_type: WorkflowScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[WorkflowRunSetResponse]:
    return [_to_set_response(item) for item in list_workflow_run_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/workflow-runs/records/{workflow_run_id}", response_model=WorkflowRunRecordResponse)
def get_workflow_run_record_route(workflow_run_id: str, session: DBSession) -> WorkflowRunRecordResponse:
    return _to_record_response(get_workflow_run_record(session, workflow_run_id))
