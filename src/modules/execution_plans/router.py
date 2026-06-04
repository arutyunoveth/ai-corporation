from fastapi import APIRouter, Query, status

from src.modules.execution_plans.schemas import (
    BuildExecutionPlanRequest,
    ExecutionPlanAssumptionResponse,
    ExecutionPlanMilestoneResponse,
    ExecutionPlanRecordResponse,
    ExecutionPlanSetResponse,
)
from src.modules.execution_plans.service import (
    build_execution_plan,
    get_execution_plan_record,
    get_execution_plan_set,
    list_execution_plan_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["execution-plans"])


def _to_record_response(result: tuple) -> ExecutionPlanRecordResponse:
    record, milestones, assumptions = result
    return ExecutionPlanRecordResponse(
        execution_plan_id=record.execution_plan_id,
        summary_text=record.summary_text,
        baseline_manifest_json=record.baseline_manifest_json,
        created_at=record.created_at,
        updated_at=record.updated_at,
        milestones=[ExecutionPlanMilestoneResponse.model_validate(item) for item in milestones],
        assumptions=[ExecutionPlanAssumptionResponse.model_validate(item) for item in assumptions],
    )


def _to_set_response(result: tuple) -> ExecutionPlanSetResponse:
    plan_set, records = result
    return ExecutionPlanSetResponse(
        execution_plan_set_id=plan_set.execution_plan_set_id,
        deal_id=plan_set.deal_id,
        plan_status=plan_set.plan_status,
        created_at=plan_set.created_at,
        updated_at=plan_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/execution-plans/build", response_model=ExecutionPlanSetResponse, status_code=status.HTTP_201_CREATED)
def build_execution_plan_route(payload: BuildExecutionPlanRequest, session: DBSession) -> ExecutionPlanSetResponse:
    plan_set = build_execution_plan(session, payload)
    return _to_set_response(get_execution_plan_set(session, plan_set.execution_plan_set_id))


@router.get("/execution-plans/{execution_plan_set_id}", response_model=ExecutionPlanSetResponse)
def get_execution_plan_set_route(execution_plan_set_id: str, session: DBSession) -> ExecutionPlanSetResponse:
    return _to_set_response(get_execution_plan_set(session, execution_plan_set_id))


@router.get("/execution-plans", response_model=list[ExecutionPlanSetResponse])
def list_execution_plan_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ExecutionPlanSetResponse]:
    return [_to_set_response(item) for item in list_execution_plan_sets(session, deal_id=deal_id)]


@router.get("/execution-plans/records/{execution_plan_id}", response_model=ExecutionPlanRecordResponse)
def get_execution_plan_record_route(execution_plan_id: str, session: DBSession) -> ExecutionPlanRecordResponse:
    return _to_record_response(get_execution_plan_record(session, execution_plan_id))
