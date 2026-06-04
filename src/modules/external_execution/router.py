from fastapi import APIRouter, Query, status

from src.modules.external_execution.schemas import (
    BuildExternalExecutionRequest,
    ExternalExecutionRecordResponse,
    ExternalExecutionResultResponse,
    ExternalExecutionSetResponse,
    StartExternalExecutionRequest,
)
from src.modules.external_execution.service import (
    build_external_execution,
    get_external_execution_record,
    get_external_execution_set,
    list_external_execution_sets,
    start_external_execution,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkspaceScopeType

router = APIRouter(tags=["external-execution"])


def _to_result_response(item) -> ExternalExecutionResultResponse:
    return ExternalExecutionResultResponse.model_validate(item)


def _to_record_response(result: tuple) -> ExternalExecutionRecordResponse:
    record, results = result
    return ExternalExecutionRecordResponse(
        external_execution_id=record.external_execution_id,
        external_execution_set_id=record.external_execution_set_id,
        integration_task_id=record.integration_task_id,
        execution_ledger_id=record.execution_ledger_id,
        gateway_action_type=record.gateway_action_type,
        request_payload_json=record.request_payload_json,
        execution_status=record.execution_status,
        started_at=record.started_at,
        finished_at=record.finished_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        results=[_to_result_response(item) for item in results],
    )


def _to_set_response(result: tuple) -> ExternalExecutionSetResponse:
    gateway_set, records = result
    return ExternalExecutionSetResponse(
        external_execution_set_id=gateway_set.external_execution_set_id,
        scope_type=gateway_set.scope_type,
        scope_ref=gateway_set.scope_ref,
        gateway_status=gateway_set.gateway_status,
        created_at=gateway_set.created_at,
        updated_at=gateway_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/external-execution/build", response_model=ExternalExecutionSetResponse, status_code=status.HTTP_201_CREATED)
def build_external_execution_route(
    payload: BuildExternalExecutionRequest,
    session: DBSession,
) -> ExternalExecutionSetResponse:
    gateway_set = build_external_execution(session, payload)
    return _to_set_response(get_external_execution_set(session, gateway_set.external_execution_set_id))


@router.post("/external-execution/start", response_model=ExternalExecutionRecordResponse, status_code=status.HTTP_201_CREATED)
def start_external_execution_route(
    payload: StartExternalExecutionRequest,
    session: DBSession,
) -> ExternalExecutionRecordResponse:
    record = start_external_execution(session, payload)
    return _to_record_response(get_external_execution_record(session, record.external_execution_id))


@router.get("/external-execution/{external_execution_set_id}", response_model=ExternalExecutionSetResponse)
def get_external_execution_set_route(
    external_execution_set_id: str,
    session: DBSession,
) -> ExternalExecutionSetResponse:
    return _to_set_response(get_external_execution_set(session, external_execution_set_id))


@router.get("/external-execution", response_model=list[ExternalExecutionSetResponse])
def list_external_execution_sets_route(
    session: DBSession,
    scope_type: WorkspaceScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[ExternalExecutionSetResponse]:
    return [_to_set_response(item) for item in list_external_execution_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/external-execution/records/{external_execution_id}", response_model=ExternalExecutionRecordResponse)
def get_external_execution_record_route(
    external_execution_id: str,
    session: DBSession,
) -> ExternalExecutionRecordResponse:
    return _to_record_response(get_external_execution_record(session, external_execution_id))
