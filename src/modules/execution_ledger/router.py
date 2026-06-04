from fastapi import APIRouter, Query, status

from src.modules.execution_ledger.schemas import (
    BuildExecutionLedgerRequest,
    ExecutionLedgerRecordResponse,
    ExecutionLedgerSetResponse,
    ExecutionResultRecordResponse,
    StartExecutionLedgerRequest,
)
from src.modules.execution_ledger.service import (
    build_execution_ledger,
    get_execution_ledger_record,
    get_execution_ledger_set,
    list_execution_ledger_sets,
    start_execution_ledger,
)
from src.shared.api.dependencies import DBSession
from src.shared.enums import WorkspaceScopeType

router = APIRouter(tags=["execution-ledger"])


def _to_result_response(item) -> ExecutionResultRecordResponse:
    return ExecutionResultRecordResponse.model_validate(item)


def _to_record_response(result: tuple) -> ExecutionLedgerRecordResponse:
    record, results = result
    return ExecutionLedgerRecordResponse(
        execution_ledger_id=record.execution_ledger_id,
        execution_ledger_set_id=record.execution_ledger_set_id,
        action_queue_id=record.action_queue_id,
        integration_task_id=record.integration_task_id,
        execution_status=record.execution_status,
        started_at=record.started_at,
        finished_at=record.finished_at,
        created_at=record.created_at,
        updated_at=record.updated_at,
        results=[_to_result_response(item) for item in results],
    )


def _to_set_response(result: tuple) -> ExecutionLedgerSetResponse:
    ledger_set, records = result
    return ExecutionLedgerSetResponse(
        execution_ledger_set_id=ledger_set.execution_ledger_set_id,
        scope_type=ledger_set.scope_type,
        scope_ref=ledger_set.scope_ref,
        ledger_status=ledger_set.ledger_status,
        created_at=ledger_set.created_at,
        updated_at=ledger_set.updated_at,
        records=[_to_record_response(item) for item in records],
    )


@router.post("/execution-ledger/build", response_model=ExecutionLedgerSetResponse, status_code=status.HTTP_201_CREATED)
def build_execution_ledger_route(
    payload: BuildExecutionLedgerRequest,
    session: DBSession,
) -> ExecutionLedgerSetResponse:
    ledger_set = build_execution_ledger(session, payload)
    return _to_set_response(get_execution_ledger_set(session, ledger_set.execution_ledger_set_id))


@router.post("/execution-ledger/start", response_model=ExecutionLedgerRecordResponse, status_code=status.HTTP_201_CREATED)
def start_execution_ledger_route(
    payload: StartExecutionLedgerRequest,
    session: DBSession,
) -> ExecutionLedgerRecordResponse:
    record = start_execution_ledger(session, payload)
    return _to_record_response(get_execution_ledger_record(session, record.execution_ledger_id))


@router.get("/execution-ledger/{execution_ledger_set_id}", response_model=ExecutionLedgerSetResponse)
def get_execution_ledger_set_route(execution_ledger_set_id: str, session: DBSession) -> ExecutionLedgerSetResponse:
    return _to_set_response(get_execution_ledger_set(session, execution_ledger_set_id))


@router.get("/execution-ledger", response_model=list[ExecutionLedgerSetResponse])
def list_execution_ledger_sets_route(
    session: DBSession,
    scope_type: WorkspaceScopeType | None = Query(default=None),
    scope_ref: str | None = Query(default=None),
) -> list[ExecutionLedgerSetResponse]:
    return [_to_set_response(item) for item in list_execution_ledger_sets(session, scope_type=scope_type, scope_ref=scope_ref)]


@router.get("/execution-ledger/records/{execution_ledger_id}", response_model=ExecutionLedgerRecordResponse)
def get_execution_ledger_record_route(execution_ledger_id: str, session: DBSession) -> ExecutionLedgerRecordResponse:
    return _to_record_response(get_execution_ledger_record(session, execution_ledger_id))
