from datetime import datetime

from src.shared.enums import WorkflowScopeType, WorkflowStatus, WorkflowStepStatus, WorkflowStepType
from src.shared.types.common import APIModel


class BuildWorkflowRunRequest(APIModel):
    scope_type: WorkflowScopeType
    scope_ref: str


class WorkflowStepRecordResponse(APIModel):
    workflow_step_id: str
    workflow_run_id: str
    step_code: str
    step_type: WorkflowStepType
    step_status: WorkflowStepStatus
    depends_on_step_ref: str | None
    source_ref: str | None
    created_at: datetime
    updated_at: datetime


class WorkflowRunRecordResponse(APIModel):
    workflow_run_id: str
    workflow_run_set_id: str
    summary_text: str
    current_phase: str
    created_at: datetime
    updated_at: datetime
    steps: list[WorkflowStepRecordResponse]


class WorkflowRunSetResponse(APIModel):
    workflow_run_set_id: str
    scope_type: WorkflowScopeType
    scope_ref: str
    workflow_status: WorkflowStatus
    created_at: datetime
    updated_at: datetime
    records: list[WorkflowRunRecordResponse]
