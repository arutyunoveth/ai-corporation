from fastapi import APIRouter, Query, status

from src.modules.execution_command.schemas import (
    BuildExecutionCommandRequest,
    ExecutionCommandBindingResponse,
    ExecutionCommandRecordResponse,
    ExecutionCommandSetResponse,
)
from src.modules.execution_command.service import (
    build_execution_command,
    get_execution_command_record,
    get_execution_command_set,
    list_execution_command_sets,
)
from src.shared.api.dependencies import DBSession

router = APIRouter(tags=["execution"])


def _to_binding_response(item) -> ExecutionCommandBindingResponse:
    return ExecutionCommandBindingResponse.model_validate(item)


def _to_record_response(item) -> ExecutionCommandRecordResponse:
    return ExecutionCommandRecordResponse.model_validate(item)


def _to_set_response(result: tuple) -> ExecutionCommandSetResponse:
    execution_set, bindings, records = result
    return ExecutionCommandSetResponse(
        execution_command_set_id=execution_set.execution_command_set_id,
        deal_id=execution_set.deal_id,
        delivery_launch_set_id=execution_set.delivery_launch_set_id,
        execution_status=execution_set.execution_status,
        created_at=execution_set.created_at,
        updated_at=execution_set.updated_at,
        bindings=[_to_binding_response(item) for item in bindings],
        records=[_to_record_response(item) for item in records],
    )


@router.post("/execution/build", response_model=ExecutionCommandSetResponse, status_code=status.HTTP_201_CREATED)
def build_execution_command_route(
    payload: BuildExecutionCommandRequest,
    session: DBSession,
) -> ExecutionCommandSetResponse:
    execution_set = build_execution_command(session, payload)
    return _to_set_response(get_execution_command_set(session, execution_set.execution_command_set_id))


@router.get("/execution/{execution_command_set_id}", response_model=ExecutionCommandSetResponse)
def get_execution_command_set_route(
    execution_command_set_id: str,
    session: DBSession,
) -> ExecutionCommandSetResponse:
    return _to_set_response(get_execution_command_set(session, execution_command_set_id))


@router.get("/execution", response_model=list[ExecutionCommandSetResponse])
def list_execution_command_sets_route(
    session: DBSession,
    deal_id: str | None = Query(default=None),
) -> list[ExecutionCommandSetResponse]:
    return [_to_set_response(item) for item in list_execution_command_sets(session, deal_id=deal_id)]


@router.get("/execution/records/{execution_command_id}", response_model=ExecutionCommandRecordResponse)
def get_execution_command_record_route(
    execution_command_id: str,
    session: DBSession,
) -> ExecutionCommandRecordResponse:
    return _to_record_response(get_execution_command_record(session, execution_command_id))
