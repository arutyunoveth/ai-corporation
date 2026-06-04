from datetime import datetime

from src.shared.enums import ExecutionPlanStatus, MilestoneState
from src.shared.types.common import APIModel


class BuildExecutionPlanRequest(APIModel):
    deal_id: str


class ExecutionPlanMilestoneResponse(APIModel):
    execution_plan_milestone_id: str
    milestone_code: str
    milestone_name: str
    due_date: datetime | None
    milestone_state: MilestoneState
    created_at: datetime
    updated_at: datetime


class ExecutionPlanAssumptionResponse(APIModel):
    assumption_code: str
    assumption_text: str
    created_at: datetime


class ExecutionPlanRecordResponse(APIModel):
    execution_plan_id: str
    summary_text: str
    baseline_manifest_json: dict
    created_at: datetime
    updated_at: datetime
    milestones: list[ExecutionPlanMilestoneResponse]
    assumptions: list[ExecutionPlanAssumptionResponse]


class ExecutionPlanSetResponse(APIModel):
    execution_plan_set_id: str
    deal_id: str
    plan_status: ExecutionPlanStatus
    created_at: datetime
    updated_at: datetime
    records: list[ExecutionPlanRecordResponse]
